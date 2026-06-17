import urllib.request


def send_ntfy(channel, message, timeout=5):
    """POST message to https://ntfy.sh/<channel>.

    Returns (ok, error): ok is True on success, error is a short string on
    failure (or None on success). Never raises — callers can surface `error`
    directly in the UI without any try/except of their own.
    """
    if not channel:
        return False, "No ntfy channel configured."
    url = f"https://ntfy.sh/{channel}"
    try:
        req = urllib.request.Request(url, data=message.encode("utf-8"), method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return True, None
            return False, f"ntfy responded with status {resp.status}"
    except Exception as e:
        return False, str(e)
