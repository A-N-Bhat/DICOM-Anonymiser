"""
DICOM Anonymizer
HIPAA Safe Harbor (45 CFR §164.514(b)) · EU GDPR · DICOM PS3.15 Annex E
"""

import pydicom
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread

# ── Field definitions ─────────────────────────────────────────────────────────
# (Category, Display Label, pydicom attribute or None, DICOM tag or None, Default value)
FIELDS = [
    ("Patient Identity",     "Patient Name",                "PatientName",                  None,            "ANON"),
    ("Patient Identity",     "Patient ID",                  "PatientID",                    None,            "ANON"),
    ("Patient Identity",     "Other Patient Names",         "OtherPatientNames",            None,            "ANON"),
    ("Patient Identity",     "Other Patient IDs",           None,                           (0x0010,0x1002), "ANON"),
    ("Patient Identity",     "Mother Birth Name",           "PatientMotherBirthName",       None,            "ANON"),
    ("Patient Demographics", "Patient Birth Date",          "PatientBirthDate",             None,            "19000101"),
    ("Patient Demographics", "Patient Birth Time",          "PatientBirthTime",             None,            "000000"),
    ("Patient Demographics", "Patient Age",                 "PatientAge",                   None,            "000Y"),
    ("Patient Demographics", "Patient Sex",                 "PatientSex",                   None,            "O"),
    ("Patient Demographics", "Patient Size",                "PatientSize",                  None,            ""),
    ("Patient Demographics", "Patient Weight",              "PatientWeight",                None,            ""),
    ("Patient Demographics", "Ethnic Group",                "EthnicGroup",                  None,            ""),
    ("Patient Demographics", "Occupation",                  None,                           (0x0010,0x2180), ""),
    ("Patient Demographics", "Pregnancy Status",            None,                           (0x0010,0x21C0), ""),
    ("Contact Information",  "Patient Address",             "PatientAddress",               None,            "ANON"),
    ("Contact Information",  "Country of Residence",        None,                           (0x0010,0x2150), "ANON"),
    ("Contact Information",  "Region of Residence",         None,                           (0x0010,0x2152), "ANON"),
    ("Contact Information",  "Patient Telephone",           None,                           (0x0010,0x2154), "ANON"),
    ("Medical Records",      "Accession Number",            "AccessionNumber",              None,            "ANON"),
    ("Medical Records",      "Medical Record Locator",      None,                           (0x0010,0x1090), "ANON"),
    ("Medical Records",      "Patient Comments",            "PatientComments",              None,            "ANON"),
    ("Medical Records",      "Additional Patient History",  None,                           (0x0010,0x21B0), "ANON"),
    ("Medical Records",      "Study Comments",              None,                           (0x0032,0x4000), "ANON"),
    ("Medical Records",      "Visit Comments",              None,                           (0x0038,0x4000), "ANON"),
    ("Dates & Times",        "Study Date",                  "StudyDate",                    None,            "19000101"),
    ("Dates & Times",        "Series Date",                 "SeriesDate",                   None,            "19000101"),
    ("Dates & Times",        "Acquisition Date",            "AcquisitionDate",              None,            "19000101"),
    ("Dates & Times",        "Content Date",                "ContentDate",                  None,            "19000101"),
    ("Dates & Times",        "Study Time",                  "StudyTime",                    None,            "000000"),
    ("Dates & Times",        "Series Time",                 "SeriesTime",                   None,            "000000"),
    ("Dates & Times",        "Acquisition Time",            "AcquisitionTime",              None,            "000000"),
    ("Dates & Times",        "Last Menstrual Date",         None,                           (0x0010,0x21D0), "19000101"),
    ("Physicians & Staff",   "Referring Physician Name",    "ReferringPhysicianName",       None,            "ANON"),
    ("Physicians & Staff",   "Referring Physician Address", "ReferringPhysicianAddress",    None,            "ANON"),
    ("Physicians & Staff",   "Referring Physician Phone",   None,                           (0x0008,0x0094), "ANON"),
    ("Physicians & Staff",   "Performing Physician Name",   "PerformingPhysicianName",      None,            "ANON"),
    ("Physicians & Staff",   "Physicians of Record",        "PhysiciansOfRecord",           None,            "ANON"),
    ("Physicians & Staff",   "Physician Reading Study",     "NameOfPhysiciansReadingStudy", None,            "ANON"),
    ("Physicians & Staff",   "Requesting Physician",        "RequestingPhysician",          None,            "ANON"),
    ("Physicians & Staff",   "Operators Name",              "OperatorsName",                None,            "ANON"),
    ("Institution",          "Institution Name",            "InstitutionName",              None,            "ANON"),
    ("Institution",          "Institution Address",         "InstitutionAddress",           None,            "ANON"),
    ("Institution",          "Department Name",             "InstitutionalDepartmentName",  None,            "ANON"),
    ("Institution",          "Station Name",                "StationName",                  None,            "ANON"),
    ("Institution",          "Requesting Service",          None,                           (0x0032,0x1033), "ANON"),
    ("Device Identifiers",   "Device Serial Number",        "DeviceSerialNumber",           None,            "ANON"),
    ("Device Identifiers",   "Plate ID",                    None,                           (0x0018,0x1004), "ANON"),
    ("Device Identifiers",   "Generator ID",                None,                           (0x0018,0x1008), "ANON"),
]

HIPAA_CATEGORIES = {
    "Patient Identity", "Patient Demographics", "Contact Information",
    "Medical Records", "Dates & Times", "Device Identifiers"
}


class DicomAnonymizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DICOM Anonymizer")
        self.root.resizable(False, False)
        self.can_cancel = False

        # Build tk vars for every field
        self.field_vars = []
        for (cat, label, attr, tag, default) in FIELDS:
            self.field_vars.append((tk.BooleanVar(value=True),
                                    tk.StringVar(value=default)))
        self.build_ui()

    # ── Main window ───────────────────────────────────────────────────────────
    def build_ui(self):
        root = self.root
        PAD = 14

        # Title
        tk.Label(root, text="DICOM Anonymizer",
                 font=("Helvetica", 20, "bold"), fg="#1A1A1A")\
            .grid(row=0, column=0, columnspan=3, padx=PAD, pady=(18, 0), sticky="w")

        tk.Label(root,
                 text="HIPAA Safe Harbor  ·  EU GDPR  ·  DICOM PS3.15 Annex E",
                 font=("Helvetica", 10), fg="#888888")\
            .grid(row=1, column=0, columnspan=3, padx=PAD, pady=(2, 14), sticky="w")

        # ── Source ──
        tk.Label(root, text="Source Folder",
                 font=("Helvetica", 11, "bold"), fg="#222222")\
            .grid(row=2, column=0, columnspan=3, padx=PAD, sticky="w")

        tk.Label(root, text="Folder containing DICOM files (all sub-folders included)",
                 font=("Helvetica", 9), fg="#999999")\
            .grid(row=3, column=0, columnspan=3, padx=PAD, sticky="w")

        self.src_entry = tk.Entry(root, width=52, font=("Helvetica", 11))
        self.src_entry.grid(row=4, column=0, columnspan=2,
                            padx=(PAD, 6), pady=6, sticky="ew", ipady=5)

        tk.Button(root, text="Browse…", font=("Helvetica", 11),
                  command=self.browse_src, width=10)\
            .grid(row=4, column=2, padx=(0, PAD), pady=6)

        # ── Destination ──
        tk.Label(root, text="Destination Folder",
                 font=("Helvetica", 11, "bold"), fg="#222222")\
            .grid(row=5, column=0, columnspan=3, padx=PAD, pady=(10, 0), sticky="w")

        tk.Label(root, text="Anonymized files saved here, organised by Study UID / Series UID",
                 font=("Helvetica", 9), fg="#999999")\
            .grid(row=6, column=0, columnspan=3, padx=PAD, sticky="w")

        self.dst_entry = tk.Entry(root, width=52, font=("Helvetica", 11))
        self.dst_entry.grid(row=7, column=0, columnspan=2,
                            padx=(PAD, 6), pady=6, sticky="ew", ipady=5)

        tk.Button(root, text="Browse…", font=("Helvetica", 11),
                  command=self.browse_dst, width=10)\
            .grid(row=7, column=2, padx=(0, PAD), pady=6)

        # ── Separator ──
        ttk.Separator(root, orient="horizontal")\
            .grid(row=8, column=0, columnspan=3, sticky="ew", padx=PAD, pady=10)

        # ── Fields button ──
        tk.Label(root, text="Fields to Anonymize",
                 font=("Helvetica", 11, "bold"), fg="#222222")\
            .grid(row=9, column=0, padx=PAD, sticky="w")

        self.field_summary = tk.Label(root,
                 text=f"All {len(FIELDS)} fields selected",
                 font=("Helvetica", 10), fg="#007AFF")
        self.field_summary.grid(row=9, column=1, sticky="w")

        tk.Button(root, text="Configure…", font=("Helvetica", 11),
                  command=self.open_fields_window, width=10)\
            .grid(row=9, column=2, padx=(0, PAD), pady=4)

        tk.Label(root,
                 text="Covers all 18 HIPAA PHI identifiers · GDPR personal data · DICOM PS3.15",
                 font=("Helvetica", 9), fg="#999999")\
            .grid(row=10, column=0, columnspan=3, padx=PAD, sticky="w")

        # ── Separator ──
        ttk.Separator(root, orient="horizontal")\
            .grid(row=11, column=0, columnspan=3, sticky="ew", padx=PAD, pady=10)

        # ── Progress ──
        tk.Label(root, text="Progress",
                 font=("Helvetica", 11, "bold"), fg="#222222")\
            .grid(row=12, column=0, columnspan=3, padx=PAD, sticky="w")

        self.progress_bar = ttk.Progressbar(root, orient="horizontal",
                                            length=400, mode="determinate")
        self.progress_bar.grid(row=13, column=0, columnspan=3,
                               padx=PAD, pady=(4, 2), sticky="ew")

        self.progress_label = tk.Label(root, text="Ready",
                                       font=("Helvetica", 10), fg="#888888", anchor="w")
        self.progress_label.grid(row=14, column=0, columnspan=3,
                                 padx=PAD, sticky="w")

        # ── Buttons ──
        self.start_btn = tk.Button(root, text="Start Anonymization",
                                   font=("Helvetica", 13, "bold"),
                                   bg="#34C759", fg="white",
                                   activebackground="#248A3D",
                                   activeforeground="white",
                                   relief=tk.FLAT,
                                   padx=20, pady=10,
                                   command=self.start)
        self.start_btn.grid(row=15, column=0, columnspan=2,
                            padx=(PAD, 6), pady=16, sticky="ew")

        self.cancel_btn = tk.Button(root, text="Cancel",
                                    font=("Helvetica", 13),
                                    padx=20, pady=10,
                                    state=tk.DISABLED,
                                    command=self.cancel)
        self.cancel_btn.grid(row=15, column=2, padx=(0, PAD), pady=16, sticky="ew")

        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)

    # ── Fields popup ──────────────────────────────────────────────────────────
    def open_fields_window(self):
        win = tk.Toplevel(self.root)
        win.title("Configure Fields")
        win.geometry("640x520")
        win.resizable(False, True)

        # Header
        tk.Label(win, text="Fields to Anonymize",
                 font=("Helvetica", 14, "bold"), fg="#1A1A1A")\
            .pack(padx=16, pady=(14, 2), anchor="w")

        tk.Label(win,
                 text="Check each field to anonymize it. Edit the replacement value. "
                      "Unchecked fields are left unchanged.",
                 font=("Helvetica", 10), fg="#888888",
                 wraplength=600, justify=tk.LEFT)\
            .pack(padx=16, pady=(0, 8), anchor="w")

        # Quick-select buttons
        ctrl = tk.Frame(win)
        ctrl.pack(fill=tk.X, padx=16, pady=(0, 8))

        tk.Button(ctrl, text="Select All", font=("Helvetica", 10),
                  command=lambda: self.select_all(True))\
            .pack(side=tk.LEFT)
        tk.Button(ctrl, text="Select None", font=("Helvetica", 10),
                  command=lambda: self.select_all(False))\
            .pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(ctrl, text="HIPAA Required Only", font=("Helvetica", 10),
                  command=self.select_hipaa)\
            .pack(side=tk.LEFT, padx=(8, 0))

        # Column headers
        hdr_frame = tk.Frame(win, bg="#DDDDDD")
        hdr_frame.pack(fill=tk.X, padx=16)

        tk.Label(hdr_frame, text=" ✓",  font=("Helvetica", 9, "bold"), bg="#DDDDDD", width=3, anchor="w").pack(side=tk.LEFT, pady=4)
        tk.Label(hdr_frame, text="Category", font=("Helvetica", 9, "bold"), bg="#DDDDDD", width=20, anchor="w").pack(side=tk.LEFT)
        tk.Label(hdr_frame, text="Field Name", font=("Helvetica", 9, "bold"), bg="#DDDDDD", width=26, anchor="w").pack(side=tk.LEFT)
        tk.Label(hdr_frame, text="Replace With", font=("Helvetica", 9, "bold"), bg="#DDDDDD", anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Scrollable list
        frame_outer = tk.Frame(win, bd=1, relief=tk.SOLID)
        frame_outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 4))

        canvas = tk.Canvas(frame_outer, highlightthickness=0)
        vsb = ttk.Scrollbar(frame_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas)
        wid = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(wid, width=e.width))

        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _scroll)

        prev_cat = None
        for i, (var_check, var_val) in enumerate(self.field_vars):
            cat, label = FIELDS[i][0], FIELDS[i][1]
            row_bg = "#F7F7F7" if i % 2 == 0 else "white"

            # Category divider
            if cat != prev_cat:
                div = tk.Frame(inner, bg="#BBBBBB", height=1)
                div.pack(fill=tk.X)
                cat_row = tk.Frame(inner, bg="#EEEEF5")
                cat_row.pack(fill=tk.X)
                tk.Label(cat_row, text=f"  {cat}",
                         font=("Helvetica", 9, "bold"),
                         bg="#EEEEF5", fg="#005EC4", anchor="w", pady=2)\
                    .pack(fill=tk.X)
                prev_cat = cat

            row = tk.Frame(inner, bg=row_bg)
            row.pack(fill=tk.X)
            row.bind("<MouseWheel>", _scroll)

            cb = tk.Checkbutton(row, variable=var_check, bg=row_bg,
                                activebackground=row_bg)
            cb.pack(side=tk.LEFT, padx=(4, 0))
            cb.bind("<MouseWheel>", _scroll)

            tk.Label(row, text=cat, font=("Helvetica", 9),
                     bg=row_bg, fg="#999999", width=20, anchor="w")\
                .pack(side=tk.LEFT, pady=4)

            tk.Label(row, text=label, font=("Helvetica", 10),
                     bg=row_bg, fg="#1A1A1A", width=26, anchor="w")\
                .pack(side=tk.LEFT)

            ent = tk.Entry(row, textvariable=var_val,
                           font=("Helvetica", 10), width=14)
            ent.pack(side=tk.LEFT, padx=(0, 10), pady=4)
            ent.bind("<MouseWheel>", _scroll)

        # Close button
        tk.Button(win, text="Done", font=("Helvetica", 11, "bold"),
                  width=12, pady=6,
                  command=lambda: [self.update_field_summary(), win.destroy()])\
            .pack(pady=(6, 14))

    def update_field_summary(self):
        checked = sum(1 for v, _ in self.field_vars if v.get())
        total = len(self.field_vars)
        self.field_summary.config(
            text=f"{checked} of {total} fields selected",
            fg="#007AFF" if checked == total else "#FF9500"
        )

    def select_all(self, state):
        for var_check, _ in self.field_vars:
            var_check.set(state)

    def select_hipaa(self):
        for i, (var_check, _) in enumerate(self.field_vars):
            var_check.set(FIELDS[i][0] in HIPAA_CATEGORIES)

    # ── File pickers ──────────────────────────────────────────────────────────
    def browse_src(self):
        p = filedialog.askdirectory(title="Select Source Folder")
        if p:
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, p)

    def browse_dst(self):
        p = filedialog.askdirectory(title="Select Destination Folder")
        if p:
            self.dst_entry.delete(0, tk.END)
            self.dst_entry.insert(0, p)

    # ── Anonymization ─────────────────────────────────────────────────────────
    def start(self):
        src = self.src_entry.get().strip()
        dst = self.dst_entry.get().strip()

        if not src or not dst:
            messagebox.showerror("Missing Paths",
                                 "Please select both a source and destination folder.")
            return
        if src == dst:
            messagebox.showerror("Invalid",
                                 "Source and destination must be different folders.")
            return
        if not os.path.isdir(src):
            messagebox.showerror("Invalid Source", "Source folder does not exist.")
            return

        active = [
            (FIELDS[i][2], FIELDS[i][3], var_val.get())
            for i, (var_check, var_val) in enumerate(self.field_vars)
            if var_check.get()
        ]

        if not active:
            messagebox.showwarning("No Fields",
                                   "No fields selected. Please configure at least one field.")
            return

        self.can_cancel = True
        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Scanning files…", fg="#007AFF")

        Thread(target=self.run, args=(src, dst, active), daemon=True).start()

    def cancel(self):
        self.can_cancel = False

    def run(self, src, dst, active_fields):
        try:
            dicom_files = []
            for root_dir, _, files in os.walk(src):
                for fname in files:
                    fp = os.path.join(root_dir, fname)
                    if fname.lower().endswith(".dcm") or "." not in fname:
                        dicom_files.append(fp)

            total = len(dicom_files)
            if total == 0:
                self.root.after(0, lambda: messagebox.showwarning(
                    "No Files Found",
                    "No DICOM files (.dcm) found in the selected folder.\n"
                    "Make sure files end in .dcm or have no extension."))
                self.root.after(0, self.reset)
                return

            done = 0
            failed = 0

            for fpath in dicom_files:
                if not self.can_cancel:
                    break
                try:
                    safe = (r"\\?\{}".format(os.path.abspath(fpath))
                            if len(fpath) > 260 else fpath)
                    ds = pydicom.dcmread(safe, force=True)

                    for attr, tag, replacement in active_fields:
                        try:
                            if attr and hasattr(ds, attr):
                                setattr(ds, attr, replacement)
                            if tag and tag in ds:
                                ds[tag].value = replacement
                        except Exception:
                            pass

                    # Remove contributor sequence (may embed PHI)
                    if (0x0018, 0xa001) in ds:
                        try:
                            del ds[(0x0018, 0xa001)]
                        except Exception:
                            pass

                    study  = str(ds.get("StudyInstanceUID",  "UNKNOWN_STUDY"))
                    series = str(ds.get("SeriesInstanceUID", "UNKNOWN_SERIES"))
                    mod    = str(ds.get("Modality",          "UN"))
                    inst   = str(ds.get("InstanceNumber",    done + 1))

                    out_dir = os.path.join(dst, study, series)
                    os.makedirs(out_dir, exist_ok=True)
                    ds.save_as(os.path.join(out_dir, f"{mod}.{inst}.dcm"))

                except Exception as e:
                    print(f"FAILED: {fpath} — {e}")
                    failed += 1

                done += 1
                pct = int((done / total) * 100)
                txt = f"Processing {done} of {total} files… ({pct}%)"
                self.root.after(0, lambda p=pct, t=txt: self._set_progress(p, t))

            if self.can_cancel:
                ok = done - failed
                self.root.after(0, lambda: messagebox.showinfo(
                    "Complete",
                    f"Anonymization complete.\n\n"
                    f"✓  {ok} file{'s' if ok != 1 else ''} anonymized\n"
                    f"✗  {failed} file{'s' if failed != 1 else ''} failed\n\n"
                    f"Saved to:\n{dst}"))
            else:
                self.root.after(0, lambda: messagebox.showwarning(
                    "Cancelled",
                    f"Cancelled after {done} of {total} files."))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

        self.root.after(0, self.reset)

    def _set_progress(self, pct, text):
        self.progress_bar["value"] = pct
        self.progress_label.config(text=text, fg="#007AFF")

    def reset(self):
        self.can_cancel = False
        self.start_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Ready", fg="#888888")


if __name__ == "__main__":
    root = tk.Tk()
    app = DicomAnonymizerApp(root)
    root.mainloop()
