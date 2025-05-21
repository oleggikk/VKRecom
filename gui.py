import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
from PIL import Image, ImageTk
from rembg import remove
import threading
from image_generator import generate_image

class DragResizeCanvas(tk.Canvas):
    HANDLE_SIZE = 8

    def __init__(self, master, bg_image, fg_image, **kwargs):
        super().__init__(master, **kwargs)
        self.bg_image = bg_image
        self.fg_image_orig = fg_image.convert("RGBA")
        self.fg_image = self.fg_image_orig.copy()
        self.fg_photo = ImageTk.PhotoImage(self.fg_image)
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        self.fg_x = 100
        self.fg_y = 100

        self.create_image(0, 0, image=self.bg_photo, anchor='nw', tags="bg")
        self.fg_id = self.create_image(self.fg_x, self.fg_y, image=self.fg_photo, anchor='nw', tags="fg")

        self.bind("<ButtonPress-1>", self.on_mouse_down)
        self.bind("<B1-Motion>", self.on_mouse_move)
        self.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.handle_selected = None
        self.dragging = False
        self.last_mouse_pos = (0, 0)

        self.rect_id = None
        self.handles = {}

        self.draw_selection_box()

    def draw_selection_box(self):
        if self.rect_id:
            self.delete(self.rect_id)
        for h in self.handles.values():
            self.delete(h)
        self.handles.clear()

        x, y = self.fg_x, self.fg_y
        w, h = self.fg_image.size
        x2, y2 = x + w, y + h

        self.rect_id = self.create_rectangle(x, y, x2, y2, outline="red", width=2)

        self.handles["tl"] = self.create_rectangle(x - self.HANDLE_SIZE//2, y - self.HANDLE_SIZE//2,
                                                   x + self.HANDLE_SIZE//2, y + self.HANDLE_SIZE//2,
                                                   fill="blue", tags="handle")
        self.handles["tr"] = self.create_rectangle(x2 - self.HANDLE_SIZE//2, y - self.HANDLE_SIZE//2,
                                                   x2 + self.HANDLE_SIZE//2, y + self.HANDLE_SIZE//2,
                                                   fill="blue", tags="handle")
        self.handles["bl"] = self.create_rectangle(x - self.HANDLE_SIZE//2, y2 - self.HANDLE_SIZE//2,
                                                   x + self.HANDLE_SIZE//2, y2 + self.HANDLE_SIZE//2,
                                                   fill="blue", tags="handle")
        self.handles["br"] = self.create_rectangle(x2 - self.HANDLE_SIZE//2, y2 - self.HANDLE_SIZE//2,
                                                   x2 + self.HANDLE_SIZE//2, y2 + self.HANDLE_SIZE//2,
                                                   fill="blue", tags="handle")

    def get_handle_at_pos(self, x, y):
        items = self.find_overlapping(x, y, x, y)
        for name, handle_id in self.handles.items():
            if handle_id in items:
                return name
        return None

    def on_mouse_down(self, event):
        handle = self.get_handle_at_pos(event.x, event.y)
        if handle:
            self.handle_selected = handle
            self.last_mouse_pos = (event.x, event.y)
        else:
            items = self.find_withtag("current")
            if self.fg_id in items:
                self.dragging = True
                self.last_mouse_pos = (event.x, event.y)

    def on_mouse_move(self, event):
        if self.handle_selected:
            self.resize_by_handle(event)
        elif self.dragging:
            dx = event.x - self.last_mouse_pos[0]
            dy = event.y - self.last_mouse_pos[1]
            self.fg_x += dx
            self.fg_y += dy
            self.move(self.fg_id, dx, dy)
            self.move(self.rect_id, dx, dy)
            for h in self.handles.values():
                self.move(h, dx, dy)
            self.last_mouse_pos = (event.x, event.y)
        self.update()

    def on_mouse_up(self, event):
        self.handle_selected = None
        self.dragging = False

    def resize_by_handle(self, event):
        x, y = self.fg_x, self.fg_y
        w, h = self.fg_image.size
        last_x, last_y = self.last_mouse_pos
        dx = event.x - last_x
        dy = event.y - last_y

        min_size = 20

        if self.handle_selected == "br":
            new_w = max(min_size, w + dx)
            new_h = max(min_size, h + dy)
            self.resize_fg(new_w, new_h)
        elif self.handle_selected == "bl":
            new_w = max(min_size, w - dx)
            new_h = max(min_size, h + dy)
            if new_w != w:
                self.fg_x += dx
            self.resize_fg(new_w, new_h)
        elif self.handle_selected == "tr":
            new_w = max(min_size, w + dx)
            new_h = max(min_size, h - dy)
            if new_h != h:
                self.fg_y += dy
            self.resize_fg(new_w, new_h)
        elif self.handle_selected == "tl":
            new_w = max(min_size, w - dx)
            new_h = max(min_size, h - dy)
            if new_w != w:
                self.fg_x += dx
            if new_h != h:
                self.fg_y += dy
            self.resize_fg(new_w, new_h)

        self.coords(self.fg_id, self.fg_x, self.fg_y)
        self.draw_selection_box()
        self.last_mouse_pos = (event.x, event.y)

    def resize_fg(self, new_w, new_h):
        self.fg_image = self.fg_image_orig.resize(
            (int(new_w), int(new_h)),
            resample=Image.Resampling.LANCZOS
        )
        self.fg_photo = ImageTk.PhotoImage(self.fg_image)
        self.itemconfig(self.fg_id, image=self.fg_photo)

    def save_composite(self, filepath):
        bg_copy = self.bg_image.copy().convert("RGBA")
        fg_img = self.fg_image
        composite = Image.new("RGBA", bg_copy.size)
        composite.paste(bg_copy, (0, 0))
        composite.paste(fg_img, (int(self.fg_x), int(self.fg_y)), mask=fg_img)
        composite = composite.convert("RGB")
        composite.save(filepath)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Background Generator + Overlay")

        self.bg_image = None
        self.fg_image = None

        tk.Label(root, text="Enter prompt for background:").pack(pady=5)
        self.prompt_entry = tk.Entry(root, width=50)
        self.prompt_entry.pack(pady=5)

        self.generate_btn = tk.Button(root, text="Generate Background", command=self.generate_bg)
        self.generate_btn.pack(pady=10)

        self.progress = Progressbar(root, orient="horizontal", length=300, mode="indeterminate")
        self.progress.pack(pady=5)

        self.load_fg_btn = tk.Button(root, text="Load Foreground Image", command=self.load_foreground)
        self.load_fg_btn.pack(pady=10)

        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack()

        self.canvas = None

        self.save_btn = tk.Button(root, text="Save Composite Image", command=self.save_image, state=tk.DISABLED)
        self.save_btn.pack(pady=10)

    def generate_bg(self):
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            messagebox.showerror("Error", "Please enter a prompt.")
            return

        self.progress.start()
        self.generate_btn.config(state=tk.DISABLED)

        def task():
            try:
                img = generate_image(prompt)
                self.bg_image = img.resize((512, 512))
                self.show_canvas()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate background:\n{e}")
            finally:
                self.progress.stop()
                self.generate_btn.config(state=tk.NORMAL)

        threading.Thread(target=task, daemon=True).start()

    def load_foreground(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png, *.jpg, *.jpeg")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
            fg_no_bg = remove(img)
            self.fg_image = fg_no_bg.resize((256, 256))
            self.show_canvas()
            self.save_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load foreground image:\n{e}")

    def show_canvas(self):
        if self.bg_image is None:
            return

        if self.canvas:
            self.canvas.destroy()

        fg_img = self.fg_image if self.fg_image is not None else Image.new("RGBA", (1, 1), (0, 0, 0, 0))

        self.canvas = DragResizeCanvas(self.canvas_frame, self.bg_image, fg_img, width=512, height=512)
        self.canvas.pack()

    def save_image(self):
        if self.canvas is None:
            messagebox.showerror("Error", "Nothing to save!")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG Image", "*.png")])
        if not path:
            return
        self.canvas.save_composite(path)
        messagebox.showinfo("Saved", f"Image saved to {path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
