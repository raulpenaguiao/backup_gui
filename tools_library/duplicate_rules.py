import os
import re
import json
import tools_library.tracer as tracer
from tools_library.drive_variables import rules_file as _RULES_FILE

RULE_TYPES = {
    "path_contains": "Path contains text",
    "path_regex":    "Path matches regex",
    "in_folder":     "File is inside folder",
    "extension":     "File extension equals",
}

RULE_ACTIONS = ["delete", "keep"]


def _path(vault_path):
    return os.path.join(vault_path, _RULES_FILE)


def load_rules(vault_path):
    """Return list of rule dicts for this vault (empty list if none saved yet)."""
    p = _path(vault_path)
    if not os.path.exists(p):
        return []
    try:
        with open(p) as f:
            return json.load(f)
    except Exception as e:
        tracer.log(f"Error loading rules from {p}: {e}")
        return []


def save_rules(vault_path, rules):
    p = _path(vault_path)
    try:
        with open(p, "w") as f:
            json.dump(rules, f, indent=2)
        tracer.log(f"Saved {len(rules)} rule(s) to {p!r}")
    except Exception as e:
        tracer.log(f"Error saving rules to {p}: {e}")


def add_rule(vault_path, rule):
    """Append a rule dict and persist. Returns updated list."""
    rules = load_rules(vault_path)
    rules.append(rule)
    save_rules(vault_path, rules)
    return rules


def remove_rule(vault_path, index):
    """Remove rule at index and persist. Returns updated list."""
    rules = load_rules(vault_path)
    if 0 <= index < len(rules):
        removed = rules.pop(index)
        save_rules(vault_path, rules)
        tracer.log(f"Removed rule {index!r}: {removed.get('name')!r}")
    return rules


def file_matches_rule(rule, file_path, vault_path):
    """Return True if file_path (absolute) matches the given rule."""
    try:
        rel = os.path.relpath(os.path.normpath(file_path), os.path.normpath(vault_path))
        rel_fwd = rel.replace(os.sep, "/")
        pattern = rule.get("pattern", "")
        rtype = rule.get("type", "")

        if rtype == "path_contains":
            return pattern.lower() in rel_fwd.lower()

        elif rtype == "path_regex":
            return bool(re.search(pattern, rel_fwd))

        elif rtype == "in_folder":
            folder = pattern.strip("/")
            return rel_fwd.startswith(folder + "/") or rel_fwd == folder

        elif rtype == "extension":
            ext = os.path.splitext(rel_fwd)[1].lower()
            pat = pattern.lower()
            if not pat.startswith("."):
                pat = "." + pat
            return ext == pat

    except Exception as e:
        tracer.log(f"Rule match error for {file_path!r}: {e}")
    return False


def apply_rules(rules, file_paths, vault_path):
    """
    For each path determine which rules fire.
    Returns dict: path -> list of (rule_name, action) for every matching rule.
    """
    result = {}
    for p in file_paths:
        matches = [(r["name"], r["action"]) for r in rules
                   if file_matches_rule(r, p, vault_path)]
        result[p] = matches
    return result


def net_action(rule_matches):
    """
    Given list of (name, action) tuples for one file, return the net verdict:
      "delete"   — only delete rules fired, no keep rules
      "keep"     — only keep rules fired, no delete rules
      "conflict" — both delete and keep rules fired
      None       — no rules fired
    """
    actions = {a for _, a in rule_matches}
    if not actions:
        return None
    if actions == {"delete"}:
        return "delete"
    if actions == {"keep"}:
        return "keep"
    return "conflict"
