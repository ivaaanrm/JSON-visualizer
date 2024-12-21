import base64
import os
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import json
from typing import Any, Dict, List, Union
import pathlib
from PIL import Image, ImageTk
import fitz

class JsonTreeExplorer:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Tree Explorer")
        self.root.geometry("1200x800")
        
        # Create main container
        self.main_container = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for tree
        self.left_frame = ttk.Frame(self.main_container)
        self.main_container.add(self.left_frame, weight=1)
        
        # Right panel with notebook for different views
        self.right_frame = ttk.Frame(self.main_container)
        self.main_container.add(self.right_frame, weight=2)
        
        # Setup components
        self.setup_menu()
        self.setup_tree()
        self.setup_notebook()
        
        # Initialize variables
        self.current_json: Dict = {}
        self.current_file: str = ""
        self.temp_files = []  # Keep track of temporary files
        
    def setup_menu(self):
        """Setup the menu bar with File options"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.load_json)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.cleanup_and_exit)
        
    def setup_tree(self):
        """Setup the treeview for JSON structure"""
        # Add search frame
        search_frame = ttk.Frame(self.left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        # Create tree
        self.tree = ttk.Treeview(self.left_frame)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure the tag for search matches
        self.tree.tag_configure('search_match', background='yellow')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    def setup_value_display(self):
        """Setup the text widget for displaying values"""
        self.value_display = scrolledtext.ScrolledText(self.right_frame, wrap=tk.WORD)
        self.value_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def load_json(self):
        """Load JSON file and populate tree"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.current_json = json.load(file)
                self.current_file = file_path
                
            # Clear existing tree
            self.tree.delete(*self.tree.get_children())
            
            # Populate tree
            self.populate_tree("", self.current_json)
            
            # Update window title
            self.root.title(f"JSON Tree Explorer - {pathlib.Path(file_path).name}")
            
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to load JSON file:\n{str(e)}")
            
    def populate_tree(self, parent: str, data: Union[Dict, List, Any], path: str = "") -> None:
        """Recursively populate the tree with JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}/{key}" if path else key
                item_id = self.tree.insert(parent, tk.END, text=key, values=(current_path,))
                self.populate_tree(item_id, value, current_path)
                
        elif isinstance(data, list):
            for index, value in enumerate(data):
                current_path = f"{path}/{index}" if path else str(index)
                item_id = self.tree.insert(parent, tk.END, text=f"[{index}]", values=(current_path,))
                self.populate_tree(item_id, value, current_path)
                
        else:
            # For primitive values, show preview in tree
            preview = str(data)
            if len(preview) > 50:
                preview = preview[:47] + "..."
            self.tree.insert(parent, tk.END, text=preview, values=(path,))
            
    def get_value_at_path(self, path: str) -> Any:
        """Get value from JSON data using path"""
        if not path:
            return self.current_json
            
        current = self.current_json
        parts = path.split("/")
        
        for part in parts:
            if part:  # Skip empty parts
                try:
                    if part.isdigit():  # Handle list indices
                        current = current[int(part)]
                    else:
                        current = current[part]
                except (KeyError, IndexError):
                    return None
                    
        return current
        
    def on_tree_select(self, event):
        """Handle tree selection event"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        # Get the path from the selected item
        path = self.tree.item(selected_items[0])["values"][0]
        
        # Get and display the value
        value = self.get_value_at_path(path)
        if value is not None:
            # Check if this is a document from lista_documentos
            try:
                path_parts = path.split('/')
                if 'nombre_documentos' in path_parts:
                    doc_index = int(path_parts[-1])
                    if doc_index < len(self.current_json.get('nombre_documentos', [])):
                        filename = self.current_json['nombre_documentos'][doc_index]
                        value = self.current_json['lista_documentos'][doc_index]
                        self.render_document(value, filename)
                        return
            except (ValueError, IndexError):
                print("Error parsing document path")
            
            # For non-document values, show in text view
            if isinstance(value, (dict, list)):
                formatted_value = json.dumps(value, indent=4)
            else:
                formatted_value = str(value)
                
            self.value_display.delete(1.0, tk.END)
            self.value_display.insert(tk.END, formatted_value)
            self.notebook.select(0)  # Switch to text view    
             
    def on_search_change(self, var_name, index, mode):
        """Handle search input changes"""
        search_text = self.search_var.get().lower()
        
        # Clear all tags by setting them to empty
        for item in self.get_all_items():
            self.tree.item(item, tags=())
            
        if not search_text:
            return
            
        def search_in_tree(node):
            item_text = self.tree.item(node)['text'].lower()
            if search_text in item_text:
                self.tree.item(node, tags=('search_match',))
                self.tree.see(node)  # Scroll to the first match
                
            for child in self.tree.get_children(node):
                search_in_tree(child)
                
        # Search through all items
        for item in self.tree.get_children():
            search_in_tree(item)
            
    def get_all_items(self, item=""):
        """Get all items in the tree"""
        children = self.tree.get_children(item)
        items = list(children)
        for child in children:
            items.extend(self.get_all_items(child))
        return items

    def get_document_index(self, filename: str) -> int:
        """Get the index of a document in the lista_documentos array"""
        try:
            return self.current_json['nombre_documentos'].index(filename)
        except (ValueError, KeyError):
            return None

    def save_current_document(self):
        """Save the currently displayed document"""
        if not self.current_doc_name:
            return
            
        try:
            # Ask user for save location
            save_path = filedialog.asksaveasfilename(
                defaultextension=os.path.splitext(self.current_doc_name)[1],
                initialfile=self.current_doc_name,
                filetypes=[("All files", "*.*")]
            )
            
            if save_path:
                # Find the document in the JSON data
                doc_index = self.get_document_index(self.current_doc_name)
                if doc_index is not None:
                    # Get base64 data
                    base64_data = self.current_json['lista_documentos'][doc_index]
                    
                    # Decode and save
                    with open(save_path, 'wb') as f:
                        f.write(base64.b64decode(base64_data))
                    
                    messagebox.showinfo("Success", "Document saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save document: {str(e)}")
          
    def update_page_controls(self):
        """Update page navigation controls"""
        current_page = self.current_page + 1
        self.page_label.config(text=f"Page: {current_page}/{self.total_pages}")
        
        # Update button states
        self.prev_button.state(['!disabled'] if current_page > 1 else ['disabled'])
        self.next_button.state(['!disabled'] if current_page < self.total_pages else ['disabled'])

    def prev_page(self):
        """Show previous page"""
        if isinstance(self.current_document, fitz.Document):
            if self.current_page > 0:
                self.current_page -= 1
                self.show_current_page()

    def next_page(self):
        """Show next page"""
        if isinstance(self.current_document, fitz.Document):
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                self.show_current_page()

    def show_current_page(self):
        """Show the current page of the PDF"""
        if not isinstance(self.current_document, fitz.Document):
            return
            
        try:
            # Clear current display
            self.doc_canvas.delete("all")
            
            # Get the page
            page = self.current_document[self.current_page]
            
            # Convert to image
            pix = page.get_pixmap()
            
            # Convert to PIL Image
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Resize to fit canvas
            canvas_width = self.doc_canvas.winfo_width()
            canvas_height = self.doc_canvas.winfo_height()
            image.thumbnail((canvas_width, canvas_height))
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # Keep a reference
            self._current_photo = photo
            
            # Display in canvas
            self.doc_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
            
            # Update navigation controls
            self.update_page_controls()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show page: {str(e)}")

    def render_document(self, base64_data: str, filename: str):
        """Render document based on its file type"""
        try:
            # Clean up previous temp files
            self.cleanup_temp_files()
            
            # Decode base64 data
            file_data = base64.b64decode(base64_data)
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(file_data)
                temp_path = temp_file.name
                self.temp_files.append(temp_path)
            
            self.current_doc_name = filename
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                self.render_image(temp_path)
            elif file_ext == '.pdf':
                self.render_pdf(temp_path)
            else:
                # For other file types, show preview in text view
                self.value_display.delete(1.0, tk.END)
                self.value_display.insert(tk.END, f"File type {file_ext} preview not supported.\nUse the Save Document button to save and open externally.")
                self.notebook.select(0)  # Switch to text view
        except Exception as e:
            messagebox.showerror("Error", f"Failed to render document: {str(e)}")

    def render_pdf(self, pdf_path: str):
        """Render PDF in the document view"""
        try:
            # Open PDF document
            self.current_document = fitz.open(pdf_path)
            self.total_pages = len(self.current_document)
            self.current_page = 0
            self.show_current_page()
            
            # Switch to document view
            self.notebook.select(1)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to render PDF: {str(e)}")

    def render_image(self, image_path: str):
        """Render image in the document view"""
        try:
            # Clear current display
            self.doc_canvas.delete("all")
            
            # Load and display image
            image = Image.open(image_path)
            # Resize image to fit canvas while maintaining aspect ratio
            canvas_width = self.doc_canvas.winfo_width()
            canvas_height = self.doc_canvas.winfo_height()
            image.thumbnail((canvas_width, canvas_height))
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # Keep a reference to prevent garbage collection
            self.current_document = photo
            
            # Display in canvas
            self.doc_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
            
            # Update navigation controls
            self.current_page = 1
            self.total_pages = 1
            self.update_page_controls()
            
            # Switch to document view
            self.notebook.select(1)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to render image: {str(e)}")

    def cleanup_temp_files(self):
        """Clean up any temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Error cleaning up {temp_file}: {e}")
        self.temp_files = []

    def cleanup_and_exit(self):
        """Clean up temporary files and exit"""
        self.cleanup_temp_files()
        self.root.quit()

    def setup_notebook(self):
        """Setup notebook with tabs for different views"""
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Text view tab
        self.text_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.text_frame, text='Text View')
        
        self.value_display = scrolledtext.ScrolledText(self.text_frame, wrap=tk.WORD)
        self.value_display.pack(fill=tk.BOTH, expand=True)
        
        # Document view tab
        self.doc_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.doc_frame, text='Document View')
        
        # Create canvas for document display
        self.doc_canvas = tk.Canvas(self.doc_frame, bg='white')
        self.doc_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for document view
        self.doc_scrollbar = ttk.Scrollbar(self.doc_frame, orient=tk.VERTICAL, command=self.doc_canvas.yview)
        self.doc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.doc_canvas.configure(yscrollcommand=self.doc_scrollbar.set)
        
        # Document controls frame
        self.doc_controls = ttk.Frame(self.doc_frame)
        self.doc_controls.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation buttons for multiple page documents
        self.prev_button = ttk.Button(self.doc_controls, text="Previous", command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.next_button = ttk.Button(self.doc_controls, text="Next", command=self.next_page)
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        self.page_label = ttk.Label(self.doc_controls, text="Page: 0/0")
        self.page_label.pack(side=tk.LEFT, padx=5)
        
        # Save button
        self.save_button = ttk.Button(self.doc_controls, text="Save Document", command=self.save_current_document)
        self.save_button.pack(side=tk.RIGHT, padx=5)
        
        # Initialize document viewing variables
        self.current_document = None
        self.current_page = 0
        self.total_pages = 0
        self.current_doc_name = ""

if __name__ == "__main__":
    root = tk.Tk()
    app = JsonTreeExplorer(root)
    root.mainloop()