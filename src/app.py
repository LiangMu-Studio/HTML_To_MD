import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from converter import Converter


class HTMLToMDApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HTML ↔ Markdown Converter")
        self.root.geometry("900x600")
        self.root.resizable(True, True)

        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title = ttk.Label(main_frame, text="HTML ↔ Markdown Converter", font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=10)

        # Input section
        input_label = ttk.Label(main_frame, text="Input:", font=("Arial", 10, "bold"))
        input_label.grid(row=1, column=0, sticky=tk.W, pady=(10, 5))

        self.input_text = tk.Text(main_frame, height=12, width=40, wrap=tk.WORD)
        self.input_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # Scrollbar for input
        input_scroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        input_scroll.grid(row=2, column=0, sticky=(tk.E, tk.N, tk.S), padx=(0, 0))
        self.input_text.config(yscrollcommand=input_scroll.set)

        # Output section
        output_label = ttk.Label(main_frame, text="Output:", font=("Arial", 10, "bold"))
        output_label.grid(row=1, column=1, sticky=tk.W, pady=(10, 5))

        self.output_text = tk.Text(main_frame, height=12, width=40, wrap=tk.WORD)
        self.output_text.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        # Scrollbar for output
        output_scroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        output_scroll.grid(row=2, column=1, sticky=(tk.E, tk.N, tk.S), padx=(0, 0))
        self.output_text.config(yscrollcommand=output_scroll.set)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)

        # Buttons
        ttk.Button(button_frame, text="HTML → Markdown", command=self.html_to_md).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Markdown → HTML", command=self.md_to_html).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Open File", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Output", command=self.save_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=5)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

    def html_to_md(self):
        try:
            html = self.input_text.get("1.0", tk.END)
            if not html.strip():
                messagebox.showwarning("Warning", "Please enter HTML content")
                return
            md = Converter.html_to_markdown(html)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", md)
            self.status_var.set("✓ HTML converted to Markdown")
        except Exception as e:
            messagebox.showerror("Error", f"Conversion failed: {str(e)}")
            self.status_var.set("✗ Conversion failed")

    def md_to_html(self):
        try:
            md = self.input_text.get("1.0", tk.END)
            if not md.strip():
                messagebox.showwarning("Warning", "Please enter Markdown content")
                return
            html = Converter.markdown_to_html(md)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", html)
            self.status_var.set("✓ Markdown converted to HTML")
        except Exception as e:
            messagebox.showerror("Error", f"Conversion failed: {str(e)}")
            self.status_var.set("✗ Conversion failed")

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("All files", "*.*"), ("HTML files", "*.html"), ("Markdown files", "*.md"), ("Text files", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", content)
                self.status_var.set(f"✓ Opened: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")

    def save_file(self):
        content = self.output_text.get("1.0", tk.END)
        if not content.strip():
            messagebox.showwarning("Warning", "No content to save")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("All files", "*.*"), ("HTML files", "*.html"), ("Markdown files", "*.md"), ("Text files", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_var.set(f"✓ Saved: {os.path.basename(file_path)}")
                messagebox.showinfo("Success", f"File saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def clear(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self.status_var.set("Ready")


if __name__ == "__main__":
    root = tk.Tk()
    app = HTMLToMDApp(root)
    root.mainloop()
