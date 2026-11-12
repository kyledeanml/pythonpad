#!/usr/bin/env python3
"""
PythonPanel - Project File Structure Tree & Sidebar
Provides hierarchical directory browsing, folder expand/collapse, file activation,
context actions (New File, New Folder, Rename, Delete, Reveal in File Manager),
and toggleable sidebar state for traditional IDE workflow.
"""

import os
import shutil
import subprocess
import sys
from typing import Callable, List, Optional, Set

sys.dont_write_bytecode = True

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, Pango, GLib, GObject, Gio


# Standard directories and file patterns ignored by default in IDE trees
IGNORED_DIRS = {
    '.git',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.venv',
    'venv',
    'env',
    '.env',
    '.tox',
    '.idea',
    '.vscode',
    'node_modules',
    '.eggs',
}

IGNORED_EXTENSIONS = ('.pyc', '.pyo', '.swp', '.swo', '~')


class ProjectSidebar(Gtk.Box):
    """
    Project File Structure sidebar panel for PythonPanel.
    Displays an interactive directory tree with expand/collapse, file opening,
    refresh, and right-click management tools.
    """

    __gsignals__ = {
        'file-activated': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'file-renamed': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        'file-deleted': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'project-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'close-requested': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    # Model columns: (icon_name, display_name, full_path, is_dir, is_loaded)
    COL_ICON = 0
    COL_NAME = 1
    COL_PATH = 2
    COL_IS_DIR = 3
    COL_LOADED = 4

    def __init__(self, project_root: Optional[str] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("project-sidebar")
        Gtk.StyleContext.add_class(self.get_style_context(), "sidebar-box")

        self.project_root: Optional[str] = None
        self.show_hidden = False
        self.get_active_file_callback: Optional[Callable[[], Optional[str]]] = None

        self._build_header()
        self._build_tree_area()

        if project_root and os.path.isdir(project_root):
            self.set_project_root(project_root)
        else:
            self._show_empty_state()

    # --------------------------------------------------------------------------
    # Header UI
    # --------------------------------------------------------------------------
    def _build_header(self):
        self.header_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.header_bar.set_name("sidebar-header")
        Gtk.StyleContext.add_class(self.header_bar.get_style_context(), "sidebar-header")
        self.header_bar.set_margin_start(8)
        self.header_bar.set_margin_end(6)
        self.header_bar.set_margin_top(6)
        self.header_bar.set_margin_bottom(6)

        # Title: Folder icon + Project folder name (clickable to open folder)
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        icon = Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.MENU)
        title_box.pack_start(icon, False, False, 0)

        self.lbl_project = Gtk.Label(label="PROJECT")
        self.lbl_project.set_xalign(0)
        self.lbl_project.set_ellipsize(Pango.EllipsizeMode.END)
        Gtk.StyleContext.add_class(self.lbl_project.get_style_context(), "sidebar-title")
        title_box.pack_start(self.lbl_project, True, True, 0)

        ev_title = Gtk.EventBox()
        ev_title.add(title_box)
        ev_title.connect("button-press-event", lambda w, e: self.on_open_folder_dialog())
        ev_title.set_tooltip_text("Click to open or switch project folder")
        self.header_bar.pack_start(ev_title, True, True, 0)

        # Action Button Box (linked)
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)

        # 0. Open Project Folder
        self.btn_open_folder = Gtk.Button.new_from_icon_name("folder-open-symbolic", Gtk.IconSize.MENU)
        self.btn_open_folder.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_open_folder.set_tooltip_text("Open Project Folder...")
        self.btn_open_folder.connect("clicked", lambda b: self.on_open_folder_dialog())
        actions_box.pack_start(self.btn_open_folder, False, False, 0)

        # 1. New File in Project
        self.btn_new_file = Gtk.Button.new_from_icon_name("document-new-symbolic", Gtk.IconSize.MENU)
        self.btn_new_file.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_new_file.set_tooltip_text("New File in Project")
        self.btn_new_file.connect("clicked", lambda b: self.on_new_file())
        actions_box.pack_start(self.btn_new_file, False, False, 0)

        # 2. New Folder in Project
        self.btn_new_folder = Gtk.Button.new_from_icon_name("folder-new-symbolic", Gtk.IconSize.MENU)
        self.btn_new_folder.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_new_folder.set_tooltip_text("New Folder in Project")
        self.btn_new_folder.connect("clicked", lambda b: self.on_new_folder())
        actions_box.pack_start(self.btn_new_folder, False, False, 0)

        # 3. Refresh Tree
        self.btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.MENU)
        self.btn_refresh.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_refresh.set_tooltip_text("Refresh Project Tree")
        self.btn_refresh.connect("clicked", lambda b: self.refresh())
        actions_box.pack_start(self.btn_refresh, False, False, 0)

        # 4. Collapse All
        self.btn_collapse = Gtk.Button.new_from_icon_name("format-indent-less-symbolic", Gtk.IconSize.MENU)
        self.btn_collapse.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_collapse.set_tooltip_text("Collapse All Folders")
        self.btn_collapse.connect("clicked", lambda b: self.collapse_all())
        actions_box.pack_start(self.btn_collapse, False, False, 0)

        # 5. Hide Sidebar
        self.btn_close = Gtk.Button.new_from_icon_name("pan-start-symbolic", Gtk.IconSize.MENU)
        self.btn_close.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_close.set_tooltip_text("Hide Project Sidebar (Ctrl+B or F9)")
        self.btn_close.connect("clicked", lambda b: self.emit("close-requested"))
        actions_box.pack_start(self.btn_close, False, False, 0)

        self.header_bar.pack_end(actions_box, False, False, 0)
        self.pack_start(self.header_bar, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(sep, False, False, 0)

    # --------------------------------------------------------------------------
    # Tree Area
    # --------------------------------------------------------------------------
    def _build_tree_area(self):
        # Tree View in ScrolledWindow (Directly packed, always rendered & visible)
        self.scrolled_tree = Gtk.ScrolledWindow()
        self.scrolled_tree.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # Store: icon_name, name, full_path, is_dir, is_loaded
        self.store = Gtk.TreeStore(str, str, str, bool, bool)
        self.tree_view = Gtk.TreeView(model=self.store)
        self.tree_view.set_headers_visible(False)
        self.tree_view.set_enable_search(True)
        self.tree_view.set_search_column(self.COL_NAME)
        self.tree_view.set_activate_on_single_click(True)

        col = Gtk.TreeViewColumn("Project Files")
        col.set_spacing(6)

        # Icon renderer
        render_pix = Gtk.CellRendererPixbuf()
        col.pack_start(render_pix, False)
        col.add_attribute(render_pix, "icon_name", self.COL_ICON)

        # Text renderer
        render_text = Gtk.CellRendererText()
        render_text.set_property("ellipsize", Pango.EllipsizeMode.END)
        col.pack_start(render_text, True)
        col.add_attribute(render_text, "text", self.COL_NAME)

        self.tree_view.append_column(col)

        self.tree_view.connect("row-activated", self._on_row_activated)
        self.tree_view.connect("row-expanded", self._on_row_expanded)
        self.tree_view.connect("row-collapsed", self._on_row_collapsed)
        self.tree_view.connect("button-press-event", self._on_tree_button_press)

        self.scrolled_tree.add(self.tree_view)
        self.pack_start(self.scrolled_tree, True, True, 0)

    # --------------------------------------------------------------------------
    # Project Root Management
    # --------------------------------------------------------------------------
    def set_project_root(self, root_path: str):
        """Set the active project root directory and scan its immediate tree."""
        if not root_path or not os.path.isdir(root_path):
            self._show_empty_state()
            return

        abs_root = os.path.abspath(root_path)
        self.project_root = abs_root

        base_name = os.path.basename(abs_root) or abs_root
        self.lbl_project.set_text(base_name)
        self.lbl_project.set_tooltip_text(abs_root)

        self.refresh()
        self.emit("project-changed", abs_root)

    def get_project_root(self) -> Optional[str]:
        return self.project_root

    def _show_empty_state(self):
        self.project_root = None
        self.lbl_project.set_text("NO PROJECT")
        self.lbl_project.set_tooltip_text("Click to open or choose a project folder")
        self.store.clear()
        # Add prominent actionable items directly in the tree so user never sees a blank space
        self.store.append(None, [
            "folder-open-symbolic",
            "Open Project Folder...",
            "__ACTION_OPEN_FOLDER__",
            False,
            True
        ])
        if self.get_active_file_callback:
            active_f = self.get_active_file_callback()
            if active_f and os.path.exists(active_f):
                parent_dir = os.path.dirname(os.path.abspath(active_f))
                base_p = os.path.basename(parent_dir) or parent_dir
                self.store.append(None, [
                    "folder-symbolic",
                    f"Open Current File Folder ({base_p})",
                    f"__ACTION_OPEN_PARENT__{parent_dir}",
                    False,
                    True
                ])

    def refresh(self):
        """Rescan project directory while preserving user's expanded folder state."""
        if not self.project_root or not os.path.isdir(self.project_root):
            self._show_empty_state()
            return

        expanded_paths = self._get_expanded_paths()
        self.store.clear()

        # Populate top level items of project_root
        self._populate_directory(None, self.project_root)

        # Restore expanded folders
        if expanded_paths:
            self._restore_expanded_paths(expanded_paths)

    def collapse_all(self):
        """Collapse all folders in the project tree."""
        self.tree_view.collapse_all()

    # --------------------------------------------------------------------------
    # Tree Population & Dynamic Lazy Loading
    # --------------------------------------------------------------------------
    def _populate_directory(self, parent_iter: Optional[Gtk.TreeIter], dir_path: str):
        """Read directory entries, sort folders first, and append to TreeStore."""
        try:
            entries = list(os.scandir(dir_path))
        except (PermissionError, FileNotFoundError, OSError):
            return

        dirs = []
        files = []

        for e in entries:
            name = e.name
            if not self.show_hidden and name.startswith('.'):
                continue
            if not self.show_hidden and name in IGNORED_DIRS:
                continue
            if not self.show_hidden and any(name.endswith(ext) for ext in IGNORED_EXTENSIONS):
                continue

            try:
                is_dir = e.is_dir(follow_symlinks=False)
            except OSError:
                is_dir = False

            if is_dir:
                dirs.append(e)
            else:
                files.append(e)

        dirs.sort(key=lambda x: x.name.lower())
        files.sort(key=lambda x: x.name.lower())

        # Add subdirectories
        for d in dirs:
            icon = "folder"
            child_iter = self.store.append(parent_iter, [
                icon,
                d.name,
                d.path,
                True,
                False  # is_loaded
            ])
            # Check if directory has sub-entries to display expander arrow
            if self._dir_has_entries(d.path):
                self.store.append(child_iter, [
                    "folder",
                    "Loading...",
                    "",
                    False,
                    False
                ])

        # Add files
        for f in files:
            icon = self.get_file_icon(f.name)
            self.store.append(parent_iter, [
                icon,
                f.name,
                f.path,
                False,
                True  # is_loaded
            ])

    def _dir_has_entries(self, dir_path: str) -> bool:
        """Quick check if a directory has visible entries."""
        try:
            with os.scandir(dir_path) as it:
                for e in it:
                    name = e.name
                    if not self.show_hidden and name.startswith('.'):
                        continue
                    if not self.show_hidden and name in IGNORED_DIRS:
                        continue
                    if not self.show_hidden and any(name.endswith(ext) for ext in IGNORED_EXTENSIONS):
                        continue
                    return True
        except OSError:
            pass
        return False

    @staticmethod
    def get_file_icon(filename: str) -> str:
        """Select appropriate icon based on file extension."""
        lower = filename.lower()
        if lower.endswith((".py", ".pyw")):
            return "text-x-python"
        elif lower.endswith((".md", ".markdown", ".rst", ".txt")):
            return "text-x-generic"
        elif lower.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml")):
            return "text-x-generic"
        elif lower.endswith((".sh", ".bash", ".zsh")):
            return "text-x-script"
        elif lower.endswith((".html", ".htm", ".css", ".js", ".ts")):
            return "text-html"
        elif lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico")):
            return "image-x-generic"
        elif lower.endswith((".pdf",)):
            return "document-open-symbolic"
        return "text-x-generic"

    # --------------------------------------------------------------------------
    # Tree Events & Expand / Collapse
    # --------------------------------------------------------------------------
    def _on_row_activated(self, tree_view, path, column):
        """User clicked or pressed Enter on a tree row."""
        model = self.store
        tree_iter = model.get_iter(path)
        is_dir = model.get_value(tree_iter, self.COL_IS_DIR)
        full_path = model.get_value(tree_iter, self.COL_PATH)

        if full_path == "__ACTION_OPEN_FOLDER__":
            self.on_open_folder_dialog()
            return
        if full_path and str(full_path).startswith("__ACTION_OPEN_PARENT__"):
            parent_target = str(full_path).replace("__ACTION_OPEN_PARENT__", "")
            if os.path.isdir(parent_target):
                self.set_project_root(parent_target)
            return

        if is_dir:
            if tree_view.row_expanded(path):
                tree_view.collapse_row(path)
            else:
                tree_view.expand_row(path, False)
        else:
            if full_path and os.path.isfile(full_path):
                self.emit("file-activated", full_path)

    def _ensure_dir_loaded(self, tree_iter: Gtk.TreeIter, dir_path: str):
        """Ensure a directory node's contents are populated."""
        if not self.store.get_value(tree_iter, self.COL_LOADED):
            while self.store.iter_has_child(tree_iter):
                dummy = self.store.iter_children(tree_iter)
                self.store.remove(dummy)
            self._populate_directory(tree_iter, dir_path)
            self.store.set_value(tree_iter, self.COL_LOADED, True)
            self.store.set_value(tree_iter, self.COL_ICON, "folder-open")

    def _on_row_expanded(self, tree_view, tree_iter, path):
        """Lazy load directory contents when node is expanded."""
        is_dir = self.store.get_value(tree_iter, self.COL_IS_DIR)
        dir_path = self.store.get_value(tree_iter, self.COL_PATH)
        if is_dir and dir_path:
            self._ensure_dir_loaded(tree_iter, dir_path)

    def _on_row_collapsed(self, tree_view, tree_iter, path):
        """Change icon back to standard folder when collapsed."""
        model = self.store
        is_dir = model.get_value(tree_iter, self.COL_IS_DIR)
        if is_dir:
            model.set_value(tree_iter, self.COL_ICON, "folder")

    # --------------------------------------------------------------------------
    # State Preservation (Expanded Folders & File Highlight)
    # --------------------------------------------------------------------------
    def _get_expanded_paths(self) -> Set[str]:
        expanded = set()

        def _check_node(model, path, tree_iter):
            if self.tree_view.row_expanded(path):
                full_path = model.get_value(tree_iter, self.COL_PATH)
                if full_path:
                    expanded.add(full_path)

        self.store.foreach(_check_node)
        return expanded

    def _restore_expanded_paths(self, expanded_paths: Set[str]):
        def _expand_matching(model, path, tree_iter):
            full_path = model.get_value(tree_iter, self.COL_PATH)
            if full_path in expanded_paths:
                self._ensure_dir_loaded(tree_iter, full_path)
                self.tree_view.expand_row(path, False)

        self.store.foreach(_expand_matching)

    def highlight_file(self, file_path: str):
        """Expand parent directories and select the active file in the tree."""
        if not self.project_root or not file_path:
            return
        abs_target = os.path.abspath(file_path)
        if not abs_target.startswith(self.project_root):
            return

        # Ensure parent directories up to root are loaded and expanded
        rel_path = os.path.relpath(abs_target, self.project_root)
        parts = rel_path.split(os.sep)

        cur_dir = self.project_root
        parent_iter = None
        for p in parts[:-1]:
            cur_dir = os.path.join(cur_dir, p)
            found = False
            child = self.store.iter_children(parent_iter)
            while child:
                if self.store.get_value(child, self.COL_PATH) == cur_dir:
                    self._ensure_dir_loaded(child, cur_dir)
                    tpath = self.store.get_path(child)
                    self.tree_view.expand_row(tpath, False)
                    parent_iter = child
                    found = True
                    break
                child = self.store.iter_next(child)
            if not found:
                break

        # Select target file
        child = self.store.iter_children(parent_iter)
        while child:
            if self.store.get_value(child, self.COL_PATH) == abs_target:
                tpath = self.store.get_path(child)
                self.tree_view.get_selection().select_path(tpath)
                self.tree_view.set_cursor(tpath, None, False)
                self.tree_view.scroll_to_cell(tpath, None, True, 0.5, 0.0)
                break
            child = self.store.iter_next(child)

    # --------------------------------------------------------------------------
    # Context Menu & Actions
    # --------------------------------------------------------------------------
    def _on_tree_button_press(self, tree_view, event):
        """Right click context menu for files and folders."""
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            pos_info = tree_view.get_path_at_pos(int(event.x), int(event.y))
            if pos_info is not None:
                path, col, cell_x, cell_y = pos_info
                tree_view.set_cursor(path, col, False)
                tree_iter = self.store.get_iter(path)
                item_path = self.store.get_value(tree_iter, self.COL_PATH)
                is_dir = self.store.get_value(tree_iter, self.COL_IS_DIR)
            else:
                item_path = self.project_root
                is_dir = True

            self._show_context_menu(event, item_path, is_dir)
            return True
        return False

    def _show_context_menu(self, event, target_path: Optional[str], is_dir: bool):
        menu = Gtk.Menu()
        base_dir = target_path if is_dir else os.path.dirname(target_path) if target_path else self.project_root

        # New File
        it_new_f = Gtk.MenuItem(label="New File...")
        it_new_f.connect("activate", lambda w: self.on_new_file(base_dir))
        menu.append(it_new_f)

        # New Folder
        it_new_d = Gtk.MenuItem(label="New Folder...")
        it_new_d.connect("activate", lambda w: self.on_new_folder(base_dir))
        menu.append(it_new_d)

        menu.append(Gtk.SeparatorMenuItem())

        if target_path and target_path != self.project_root:
            # Rename
            it_ren = Gtk.MenuItem(label="Rename...")
            it_ren.connect("activate", lambda w: self.on_rename(target_path))
            menu.append(it_ren)

            # Delete
            it_del = Gtk.MenuItem(label="Delete")
            it_del.connect("activate", lambda w: self.on_delete(target_path, is_dir))
            menu.append(it_del)

            menu.append(Gtk.SeparatorMenuItem())

        # Copy Path
        if target_path:
            it_copy = Gtk.MenuItem(label="Copy Path")
            it_copy.connect("activate", lambda w: self._copy_to_clipboard(target_path))
            menu.append(it_copy)

            # Reveal in File Manager
            it_reveal = Gtk.MenuItem(label="Reveal in File Manager")
            it_reveal.connect("activate", lambda w: self._reveal_in_file_manager(target_path))
            menu.append(it_reveal)

            menu.append(Gtk.SeparatorMenuItem())

        # Show / Hide Hidden Files
        it_hidden = Gtk.CheckMenuItem(label="Show Hidden Files")
        it_hidden.set_active(self.show_hidden)
        it_hidden.connect("toggled", lambda w: self._on_toggle_hidden(w.get_active()))
        menu.append(it_hidden)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _on_toggle_hidden(self, active: bool):
        self.show_hidden = active
        self.refresh()

    def _copy_to_clipboard(self, text: str):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        if clipboard:
            clipboard.set_text(text, -1)

    def _reveal_in_file_manager(self, target_path: str):
        folder = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
        try:
            Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(folder, None), None)
        except Exception:
            try:
                subprocess.Popen(["xdg-open", folder])
            except Exception:
                pass

    # --------------------------------------------------------------------------
    # Interactive Actions: New File / Folder / Rename / Delete
    # --------------------------------------------------------------------------
    def on_new_file(self, target_dir: Optional[str] = None):
        """Prompt user for new filename, create it, refresh tree, and open tab."""
        dest_dir = target_dir or self.project_root
        if not dest_dir or not os.path.isdir(dest_dir):
            return

        dialog = Gtk.Dialog(
            title="New File",
            parent=self.get_toplevel() if isinstance(self.get_toplevel(), Gtk.Window) else None,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Create", Gtk.ResponseType.OK)
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(12)
        content.set_margin_bottom(12)

        lbl = Gtk.Label(label=f"Enter new file name in:\n{os.path.basename(dest_dir) or dest_dir}")
        lbl.set_xalign(0)
        content.pack_start(lbl, False, False, 0)

        entry = Gtk.Entry()
        entry.set_text("script.py")
        entry.set_activates_default(True)
        content.pack_start(entry, False, False, 0)

        dialog.show_all()
        resp = dialog.run()
        fname = entry.get_text().strip()
        dialog.destroy()

        if resp == Gtk.ResponseType.OK and fname:
            new_path = os.path.join(dest_dir, fname)
            try:
                if not os.path.exists(new_path):
                    with open(new_path, "w", encoding="utf-8") as f:
                        if new_path.endswith(".py"):
                            f.write("#!/usr/bin/env python3\n\"\"\"Module description.\"\"\"\n\n")
                        else:
                            f.write("")
                self.refresh()
                self.highlight_file(new_path)
                self.emit("file-activated", new_path)
            except Exception as e:
                self._show_error_dialog(f"Could not create file:\n{e}")

    def on_new_folder(self, target_dir: Optional[str] = None):
        """Prompt user for new folder name and create directory."""
        dest_dir = target_dir or self.project_root
        if not dest_dir or not os.path.isdir(dest_dir):
            return

        dialog = Gtk.Dialog(
            title="New Folder",
            parent=self.get_toplevel() if isinstance(self.get_toplevel(), Gtk.Window) else None,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Create", Gtk.ResponseType.OK)
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(12)
        content.set_margin_bottom(12)

        lbl = Gtk.Label(label=f"Enter folder name in:\n{os.path.basename(dest_dir) or dest_dir}")
        lbl.set_xalign(0)
        content.pack_start(lbl, False, False, 0)

        entry = Gtk.Entry()
        entry.set_activates_default(True)
        content.pack_start(entry, False, False, 0)

        dialog.show_all()
        resp = dialog.run()
        dname = entry.get_text().strip()
        dialog.destroy()

        if resp == Gtk.ResponseType.OK and dname:
            new_dir = os.path.join(dest_dir, dname)
            try:
                os.makedirs(new_dir, exist_ok=True)
                self.refresh()
                self.highlight_file(new_dir)
            except Exception as e:
                self._show_error_dialog(f"Could not create folder:\n{e}")

    def on_rename(self, target_path: str):
        """Prompt user to rename file or directory."""
        old_name = os.path.basename(target_path)
        parent_dir = os.path.dirname(target_path)

        dialog = Gtk.Dialog(
            title="Rename",
            parent=self.get_toplevel() if isinstance(self.get_toplevel(), Gtk.Window) else None,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Rename", Gtk.ResponseType.OK)
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(12)
        content.set_margin_bottom(12)

        lbl = Gtk.Label(label=f"Enter new name for \"{old_name}\":")
        lbl.set_xalign(0)
        content.pack_start(lbl, False, False, 0)

        entry = Gtk.Entry()
        entry.set_text(old_name)
        entry.set_activates_default(True)
        content.pack_start(entry, False, False, 0)

        dialog.show_all()
        resp = dialog.run()
        new_name = entry.get_text().strip()
        dialog.destroy()

        if resp == Gtk.ResponseType.OK and new_name and new_name != old_name:
            new_path = os.path.join(parent_dir, new_name)
            try:
                os.rename(target_path, new_path)
                self.refresh()
                self.highlight_file(new_path)
                self.emit("file-renamed", target_path, new_path)
            except Exception as e:
                self._show_error_dialog(f"Could not rename:\n{e}")

    def on_delete(self, target_path: str, is_dir: bool):
        """Prompt confirmation and delete file or directory."""
        name = os.path.basename(target_path)
        item_kind = "folder and all its contents" if is_dir else "file"

        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel() if isinstance(self.get_toplevel(), Gtk.Window) else None,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.CANCEL,
            text=f"Delete {item_kind} \"{name}\"?"
        )
        dialog.format_secondary_text("This action cannot be undone.")
        dialog.add_button("Delete", Gtk.ResponseType.OK)

        resp = dialog.run()
        dialog.destroy()

        if resp == Gtk.ResponseType.OK:
            try:
                if is_dir:
                    shutil.rmtree(target_path)
                else:
                    os.unlink(target_path)
                self.refresh()
                self.emit("file-deleted", target_path)
            except Exception as e:
                self._show_error_dialog(f"Could not delete:\n{e}")

    def on_open_folder_dialog(self):
        """Open native folder chooser dialog to select project root."""
        top = self.get_toplevel()
        dialog = Gtk.FileChooserNative.new(
            "Select Project Folder",
            top if isinstance(top, Gtk.Window) else None,
            Gtk.FileChooserAction.SELECT_FOLDER,
            "_Open",
            "_Cancel"
        )
        if self.project_root:
            dialog.set_current_folder(self.project_root)

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            folder = dialog.get_filename()
            if folder and os.path.isdir(folder):
                self.set_project_root(folder)
        dialog.destroy()

    def _on_open_active_file_folder(self):
        """Open the directory containing the currently active file in PythonPanel."""
        if self.get_active_file_callback:
            active_file = self.get_active_file_callback()
            if active_file and os.path.exists(active_file):
                d = os.path.dirname(os.path.abspath(active_file))
                self.set_project_root(d)
                self.highlight_file(active_file)
                return
        self.on_open_folder_dialog()

    def _show_error_dialog(self, message: str):
        top = self.get_toplevel()
        dialog = Gtk.MessageDialog(
            transient_for=top if isinstance(top, Gtk.Window) else None,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=message
        )
        dialog.run()
        dialog.destroy()
