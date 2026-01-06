from ..models import Message, Thread
from django.db import transaction
import hashlib

def _build_thread_graph(messages):
    msg_by_id = {msg.message_id: msg for msg in messages if msg.message_id}
    orphaned = []
    visited = set()
    
    def find_parent_in_refs(refs, msg_by_id):
        for ref_id in refs:
            if ref_id in msg_by_id:
                parent = msg_by_id[ref_id]
                if parent.id not in visited:
                    return parent
        return None
    
    for msg in messages:
        if not msg.message_id:
            orphaned.append(msg)
            continue
        
        refs = msg.references_json or []
        parent = None
        
        if refs:
            parent = find_parent_in_refs(refs, msg_by_id)
            if not parent and msg.in_reply_to and msg.in_reply_to in msg_by_id:
                candidate = msg_by_id[msg.in_reply_to]
                if candidate.id not in visited:
                    parent = candidate
        elif msg.in_reply_to and msg.in_reply_to in msg_by_id:
            candidate = msg_by_id[msg.in_reply_to]
            if candidate.id not in visited:
                parent = candidate
        
        if parent:
            msg.parent_message = parent
            visited.add(parent.id)
    
    return messages, orphaned

def _find_thread_by_subject(orphaned_msg, existing_threads, threshold=0.8):
    from difflib import SequenceMatcher
    
    subject_norm = orphaned_msg.subject_norm or ""
    if not subject_norm:
        return None
    
    for thread in existing_threads:
        thread_subject = thread.subject_norm or ""
        if not thread_subject:
            continue
        
        ratio = SequenceMatcher(None, subject_norm, thread_subject).ratio()
        if ratio >= threshold:
            date_diff = abs((orphaned_msg.date - thread.messages.order_by('date').first().date).days) if orphaned_msg.date and thread.messages.exists() else 999
            if date_diff <= 7:
                return thread
    
    return None

def _compute_thread_key(msg: Message) -> str:
    refs = msg.references_json or []
    if refs:
        root_ref = refs[0]
        return hashlib.sha256(f"ref:{root_ref}".encode("utf-8")).hexdigest()[:40]
    
    if msg.in_reply_to:
        return hashlib.sha256(f"irt:{msg.in_reply_to}".encode("utf-8")).hexdigest()[:40]
    
    if msg.content_fingerprint:
        subject = msg.subject_norm or ""
        return hashlib.sha256(f"fp:{msg.content_fingerprint}:{subject}".encode("utf-8")).hexdigest()[:40]
    
    subject = msg.subject_norm or ""
    bucket = msg.date.date().isoformat() if msg.date else "nodate"
    return hashlib.sha256(f"fallback:{subject}:{bucket}".encode("utf-8")).hexdigest()[:40]

def _detect_circular_reference(msg, parent_msg, max_depth=50):
    visited = {msg.id}
    current = parent_msg
    depth = 0
    while current and depth < max_depth:
        if current.id in visited:
            return True
        visited.add(current.id)
        current = current.parent_message
        depth += 1
    return False

def _link_by_content_fingerprint(msg, existing_messages):
    if not msg.content_fingerprint:
        return None
    for existing in existing_messages:
        if (existing.content_fingerprint and 
            existing.content_fingerprint == msg.content_fingerprint and 
            existing.id != msg.id and
            existing.thread_id):
            return existing.thread
    return None

@transaction.atomic
def rebuild_threads(limit: int = 0):
    qs = Message.objects.select_related('thread', 'parent_message').order_by("date", "id")
    if limit and limit > 0:
        qs = qs[:limit]
    
    messages = list(qs)
    if not messages:
        return 0
    
    messages, orphaned = _build_thread_graph(messages)
    
    for msg in messages:
        if msg.parent_message and _detect_circular_reference(msg, msg.parent_message):
            msg.parent_message = None
    
    thread_map = {}
    processed_messages = []
    
    for msg in messages:
        thread = None
        
        if msg.parent_message_id and msg.parent_message and msg.parent_message.thread_id:
            thread = msg.parent_message.thread
        else:
            content_thread = _link_by_content_fingerprint(msg, processed_messages)
            if content_thread:
                thread = content_thread
            else:
                tkey = _compute_thread_key(msg)
                thread = thread_map.get(tkey)
                if not thread:
                    thread, _ = Thread.objects.get_or_create(
                        thread_key=tkey,
                        defaults={"subject_norm": msg.subject_norm or ""}
                    )
                    thread_map[tkey] = thread
        
        if msg.thread_id != thread.id:
            msg.thread = thread
            update_fields = ["thread"]
            if msg.parent_message_id:
                update_fields.append("parent_message")
            msg.save(update_fields=update_fields)
        elif msg.parent_message_id:
            msg.save(update_fields=["parent_message"])
        
        processed_messages.append(msg)
    
    all_threads = list(thread_map.values())
    existing_thread_ids = [t.id for t in all_threads]
    existing_threads = Thread.objects.prefetch_related('messages').filter(id__in=existing_thread_ids) if existing_thread_ids else Thread.objects.none()
    
    for orphaned_msg in orphaned:
        thread = _find_thread_by_subject(orphaned_msg, existing_threads)
        if not thread:
            thread = _link_by_content_fingerprint(orphaned_msg, processed_messages)
        if not thread:
            tkey = _compute_thread_key(orphaned_msg)
            thread, _ = Thread.objects.get_or_create(
                thread_key=tkey,
                defaults={"subject_norm": orphaned_msg.subject_norm or ""}
            )
        orphaned_msg.thread = thread
        orphaned_msg.save(update_fields=["thread"])
    
    for thread in all_threads:
        thread.refresh_from_db()
        if not thread.root_message_id:
            root = thread.messages.order_by('date').first()
            if root:
                thread.root_message = root
                thread.save(update_fields=["root_message"])
    
    return len(messages) + len(orphaned)
