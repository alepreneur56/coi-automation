"""
thread_fetch.py
---------------
Robust thread retrieval that survives subject changes.
Direct port of the Pipedream fetch_thread step onto GraphClient.

Strategy:
  1. Primary: query by conversationId (fast path).
  2. Fallback: when conversationId returns < 2 messages, walk UP the
     In-Reply-To / References chain, hop by hop, collecting messages from
     every conversationId encountered along the way.
  3. Ultimate fallback: return whatever was found.
"""

MAX_HOPS = 5


def _extract_parent_internet_id(headers_data):
    """Pull the immediate-parent Message-ID out of headers (In-Reply-To
    preferred, falls back to last entry of References)."""
    in_reply_to = None
    references = None
    for h in headers_data:
        name = (h.get("name") or "").lower()
        val = (h.get("value") or "").strip()
        if name == "in-reply-to":
            in_reply_to = val
        elif name == "references":
            references = val
    if in_reply_to:
        return in_reply_to
    if references:
        refs = references.split()
        if refs:
            return refs[-1].strip()
    return None


def _collect_thread_via_header_walk(graph, start_msg_id, max_hops=MAX_HOPS):
    all_messages = {}
    visited_conv_ids = set()
    current_msg_id = start_msg_id
    walk_log = []
    hops = 0

    for hops in range(1, max_hops + 1):
        if not current_msg_id:
            walk_log.append({"hop": hops, "result": "no current_msg_id"})
            break
        headers_data = graph.get_message_headers(current_msg_id)
        parent_internet_id = _extract_parent_internet_id(headers_data)
        if not parent_internet_id:
            walk_log.append({
                "hop": hops,
                "result": "no_in_reply_to_or_references_header",
                "headers_count": len(headers_data),
            })
            break

        parent = graph.find_message_by_internet_id(parent_internet_id)
        if not parent or not parent.get("id"):
            walk_log.append({
                "hop": hops,
                "result": "parent_not_found_in_mailbox",
                "parent_internet_id": parent_internet_id,
            })
            break

        all_messages[parent["id"]] = parent

        parent_conv_id = parent.get("conversationId")
        if parent_conv_id and parent_conv_id not in visited_conv_ids:
            visited_conv_ids.add(parent_conv_id)
            for m in graph.search_by_conversation(parent_conv_id):
                if m.get("id"):
                    all_messages[m["id"]] = m

        walk_log.append({
            "hop": hops,
            "result": "ok",
            "parent_internet_id": parent_internet_id,
            "running_total_messages": len(all_messages),
        })
        current_msg_id = parent["id"]

    return all_messages, visited_conv_ids, hops, walk_log


def fetch_thread(graph, new_email):
    """Returns {"messages": [...oldest first...], "method": ..., ...}."""
    msg_id = new_email.get("id")
    conv_id = new_email.get("conversationId")

    # 1. Primary — conversationId search
    primary = graph.search_by_conversation(conv_id)
    if len(primary) >= 2:
        return {
            "messages": primary,
            "method": "conversationId",
            "thread_message_count": len(primary),
            "fallback_used": False,
        }

    # 2. Fallback — multi-hop walk via In-Reply-To / References
    walked, visited_convs, hops, walk_log = _collect_thread_via_header_walk(graph, msg_id)

    if walked:
        for m in primary:
            if m.get("id"):
                walked.setdefault(m["id"], m)
        if msg_id and msg_id not in walked:
            walked[msg_id] = new_email

        sorted_msgs = sorted(walked.values(), key=lambda m: m.get("sentDateTime") or "")
        return {
            "messages": sorted_msgs,
            "method": "in_reply_to_walk",
            "thread_message_count": len(sorted_msgs),
            "fallback_used": True,
            "hops_walked": hops,
            "walk_log": walk_log,
        }

    return {
        "messages": primary,
        "method": "no_history_found",
        "thread_message_count": len(primary),
        "fallback_used": False,
        "walk_log": walk_log,
    }
