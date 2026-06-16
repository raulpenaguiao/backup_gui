import os
import tkinter as tk
from tkinter import ttk, messagebox
import tools_library.tracer as tracer
from tools_library.duplicate_rules import (
    load_rules, save_rules, add_rule, remove_rule,
    file_matches_rule, RULE_TYPES, RULE_ACTIONS,
)
from widgets_library.tooltip import Tooltip


class RulesManager:
    """
    Modal dialog for managing per-vault duplicate rules.

    Rules tell the Review Duplicates panel how to handle files automatically:
      delete — pre-select this file for deletion when it appears in a group
      keep   — protect this file from being deleted (like always-keep)

    Each rule has: name, action (delete/keep), match type, and pattern.
    """

    def __init__(self, root, vault_path):
        self._root = root
        self._vault_path = vault_path
        self._rules = load_rules(vault_path)

        self._win = tk.Toplevel(root)
        self._win.title("Duplicate Rules")
        self._win.geometry("860x560")
        self._win.minsize(680, 420)
        self._win.transient(root)
        self._win.grab_set()
        self._win.resizable(True, True)

        self._build()
        self._refresh_list()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        self._win.columnconfigure(0, weight=1)
        self._win.rowconfigure(1, weight=1)

        # Header
        hdr = tk.Frame(self._win, padx=10, pady=8)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="Duplicate Rules",
                 font=("Helvetica", 13, "bold")).pack(side=tk.LEFT)
        tk.Label(hdr,
                 text=f"  vault: {self._vault_path}",
                 fg="#666", font=("Helvetica", 9)).pack(side=tk.LEFT)

        ttk.Separator(self._win, orient=tk.HORIZONTAL).grid(
            row=0, column=0, sticky="ew", pady=(48, 0))

        # Main area: rule list (left) + editor (right)
        main = tk.Frame(self._win, padx=10, pady=6)
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.rowconfigure(0, weight=1)

        self._build_list(main)
        self._build_editor(main)

        ttk.Separator(self._win, orient=tk.HORIZONTAL).grid(
            row=2, column=0, sticky="ew")

        # Footer
        foot = tk.Frame(self._win, padx=10, pady=6)
        foot.grid(row=3, column=0, sticky="ew")

        btn_remove = tk.Button(foot, text="Remove Selected Rule",
                               command=self._remove_selected)
        btn_remove.pack(side=tk.LEFT)
        Tooltip(btn_remove,
                "Permanently remove the highlighted rule from this vault's rule list.")

        tk.Button(foot, text="Close",
                  command=self._win.destroy).pack(side=tk.RIGHT)

    def _build_list(self, parent):
        lf = tk.LabelFrame(parent, text="Current rules", padx=6, pady=6)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)

        cols = ("action", "type", "pattern", "name")
        self._tv = ttk.Treeview(lf, columns=cols, show="headings",
                                 selectmode="browse")
        self._tv.heading("action",  text="Action",  anchor=tk.W)
        self._tv.heading("type",    text="Match by", anchor=tk.W)
        self._tv.heading("pattern", text="Pattern",  anchor=tk.W)
        self._tv.heading("name",    text="Name",     anchor=tk.W)
        self._tv.column("action",  width=70,  stretch=False)
        self._tv.column("type",    width=160, stretch=False)
        self._tv.column("pattern", width=200)
        self._tv.column("name",    width=160)

        self._tv.tag_configure("delete", foreground="#a00")
        self._tv.tag_configure("keep",   foreground="#060")
        self._tv.tag_configure("conflict", foreground="#a60")

        vsb = ttk.Scrollbar(lf, orient=tk.VERTICAL, command=self._tv.yview)
        self._tv.configure(yscrollcommand=vsb.set)
        self._tv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._tv.bind("<<TreeviewSelect>>", self._on_rule_select)

        # Empty-state label
        self._empty_label = tk.Label(lf,
                                      text="No rules yet. Add one using the form →",
                                      fg="#888", font=("Helvetica", 9, "italic"))

    def _build_editor(self, parent):
        ef = tk.LabelFrame(parent, text="Add new rule", padx=10, pady=8)
        ef.grid(row=0, column=1, sticky="ns")
        ef.columnconfigure(1, weight=1)

        # Name
        tk.Label(ef, text="Name:", anchor=tk.W).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 4))
        self._name_var = tk.StringVar()
        name_entry = tk.Entry(ef, textvariable=self._name_var, width=28)
        name_entry.grid(row=0, column=1, sticky="ew", pady=(0, 4))
        Tooltip(name_entry,
                "A short label for this rule, shown in the duplicate review panel.")

        # Action
        tk.Label(ef, text="Action:", anchor=tk.W).grid(
            row=1, column=0, sticky=tk.W, pady=(0, 4))
        self._action_var = tk.StringVar(value="delete")
        action_frame = tk.Frame(ef)
        action_frame.grid(row=1, column=1, sticky="w", pady=(0, 4))
        rb_del = tk.Radiobutton(action_frame, text="Delete",
                                 variable=self._action_var, value="delete",
                                 fg="#a00")
        rb_del.pack(side=tk.LEFT)
        Tooltip(rb_del,
                "Files matching this rule will be pre-selected for deletion "
                "when they appear in a duplicate group.")
        rb_keep = tk.Radiobutton(action_frame, text="Keep",
                                  variable=self._action_var, value="keep",
                                  fg="#060")
        rb_keep.pack(side=tk.LEFT, padx=(8, 0))
        Tooltip(rb_keep,
                "Files matching this rule will be protected — they will never "
                "be suggested for deletion in a duplicate group.")

        ttk.Separator(ef, orient=tk.HORIZONTAL).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=6)

        # Match type + pattern (radio group)
        tk.Label(ef, text="Match by:", anchor=tk.W,
                 font=("Helvetica", 9, "bold")).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

        self._type_var = tk.StringVar(value="path_contains")
        self._pattern_vars = {}

        type_info = [
            ("path_contains",
             "Path contains text",
             ".git",
             "True if the file's relative path (using forward slashes) contains\n"
             "this text anywhere. Case-insensitive.\n"
             "Example:  .git  →  matches notes/project/.git/config"),
            ("path_regex",
             "Path matches regex",
             r"^notes/.*\.bak$",
             "True if the relative path matches this Python regular expression.\n"
             "The match is against the full relative path with forward slashes.\n"
             "Example:  ^notes/.*\\.bak$  →  any .bak file inside notes/"),
            ("in_folder",
             "File is inside folder",
             "notes/archive",
             "True if the file lives directly inside the specified folder\n"
             "(or any sub-folder of it). Use a forward-slash relative path.\n"
             "Example:  notes/archive  →  matches notes/archive/old.txt"),
            ("extension",
             "File extension equals",
             ".tmp",
             "True if the file's extension matches (case-insensitive).\n"
             "Include the dot, or omit it — both work.\n"
             "Example:  .tmp  or  tmp  →  matches any *.tmp file"),
        ]

        for row_offset, (rtype, label, placeholder, tip) in enumerate(type_info):
            r = row_offset + 4
            rb = tk.Radiobutton(ef, text=label,
                                 variable=self._type_var, value=rtype,
                                 anchor=tk.W)
            rb.grid(row=r, column=0, sticky=tk.W)
            Tooltip(rb, tip)

            pvar = tk.StringVar(value=placeholder)
            self._pattern_vars[rtype] = pvar
            entry = tk.Entry(ef, textvariable=pvar, width=26, fg="#666")
            entry.grid(row=r, column=1, sticky="ew", padx=(4, 0))
            Tooltip(entry, tip)

            # Clear placeholder on first focus
            def _clear(e, v=pvar, ph=placeholder):
                if v.get() == ph:
                    v.set("")
                    e.widget.config(fg="black")
            entry.bind("<FocusIn>", _clear)

        ttk.Separator(ef, orient=tk.HORIZONTAL).grid(
            row=row_offset + 5, column=0, columnspan=2, sticky="ew", pady=6)

        # Add button
        btn_add = tk.Button(ef, text="Add Rule", command=self._add_rule,
                            font=("Helvetica", 9, "bold"))
        btn_add.grid(row=row_offset + 6, column=0, columnspan=2,
                     sticky="ew", pady=(0, 4))
        Tooltip(btn_add,
                "Save this rule to the vault. It will be applied the next time "
                "you open the Review Duplicates panel for this vault.")

        # Test button
        btn_test = tk.Button(ef, text="Test rule against vault",
                             command=self._test_rule)
        btn_test.grid(row=row_offset + 7, column=0, columnspan=2, sticky="ew")
        Tooltip(btn_test,
                "Count how many files currently in the vault would be matched "
                "by this rule, without making any changes.")

        self._test_result = tk.Label(ef, text="", fg="#555",
                                      font=("Helvetica", 8), wraplength=240,
                                      justify=tk.LEFT)
        self._test_result.grid(row=row_offset + 8, column=0, columnspan=2,
                                sticky=tk.W, pady=(4, 0))

    # ── List management ───────────────────────────────────────────────────────

    def _refresh_list(self):
        self._tv.delete(*self._tv.get_children())
        for rule in self._rules:
            tag = rule.get("action", "delete")
            self._tv.insert("", tk.END, tags=(tag,), values=(
                rule.get("action", ""),
                RULE_TYPES.get(rule.get("type", ""), rule.get("type", "")),
                rule.get("pattern", ""),
                rule.get("name", ""),
            ))
        if self._rules:
            self._empty_label.place_forget()
        else:
            self._empty_label.place(relx=0.5, rely=0.5, anchor="center")

    def _on_rule_select(self, _event=None):
        pass  # could populate editor for editing in future

    def _remove_selected(self):
        sel = self._tv.selection()
        if not sel:
            messagebox.showinfo("Nothing selected",
                                "Select a rule in the list to remove it.",
                                parent=self._win)
            return
        idx = self._tv.index(sel[0])
        rule = self._rules[idx]
        confirmed = messagebox.askyesno(
            "Remove rule",
            f"Remove rule \"{rule.get('name', '')}\"?\n\n"
            f"Action: {rule.get('action')}   Pattern: {rule.get('pattern')}",
            parent=self._win,
        )
        if confirmed:
            self._rules = remove_rule(self._vault_path, idx)
            self._refresh_list()

    # ── Add rule ──────────────────────────────────────────────────────────────

    def _current_rule_dict(self):
        rtype = self._type_var.get()
        pattern = self._pattern_vars[rtype].get().strip()
        name = self._name_var.get().strip()
        action = self._action_var.get()
        return {"name": name, "action": action, "type": rtype, "pattern": pattern}

    def _validate_rule(self, rule):
        if not rule["pattern"]:
            messagebox.showwarning("Missing pattern",
                                   "Please enter a pattern for this rule.",
                                   parent=self._win)
            return False
        if not rule["name"]:
            rule["name"] = f"{rule['action']} — {rule['pattern']}"
        if rule["type"] == "path_regex":
            try:
                import re
                re.compile(rule["pattern"])
            except Exception as e:
                messagebox.showwarning("Invalid regex",
                                       f"The pattern is not a valid regular expression:\n{e}",
                                       parent=self._win)
                return False
        return True

    def _add_rule(self):
        rule = self._current_rule_dict()
        if not self._validate_rule(rule):
            return
        self._rules = add_rule(self._vault_path, rule)
        self._refresh_list()
        tracer.log(f"Rule added: {rule}", trace_level=3)

    # ── Test rule ─────────────────────────────────────────────────────────────

    def _test_rule(self):
        rule = self._current_rule_dict()
        if not rule["pattern"]:
            self._test_result.config(text="Enter a pattern first.")
            return
        self._test_result.config(text="Counting matches…")
        self._win.update_idletasks()
        count = 0
        examples = []
        for dirpath, _, filenames in os.walk(self._vault_path):
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                if file_matches_rule(rule, fp, self._vault_path):
                    count += 1
                    if len(examples) < 3:
                        rel = os.path.relpath(fp, self._vault_path)
                        examples.append(rel)
        if count == 0:
            msg = "No files in the vault match this rule."
        else:
            sample = "\n  ".join(examples)
            more = f"\n  … and {count - len(examples)} more" if count > len(examples) else ""
            msg = f"{count} file(s) match.\nExamples:\n  {sample}{more}"
        self._test_result.config(text=msg)
