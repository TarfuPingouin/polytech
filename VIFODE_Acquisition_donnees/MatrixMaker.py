import tkinter as tk
from tkinter import simpledialog, messagebox

GRID_SIZE = 8
CELL_SIZE = 45
CELL_PADDING = 4

OFF_COLOR = "#1f1f1f"
ON_COLOR = "#00ff66"
GRID_BG = "#2b2b2b"


class LedMatrixEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Éditeur matrice LED 8x8 Arduino")

        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.cells = []

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack()

        title = tk.Label(
            main_frame,
            text="Clique sur les pixels pour les allumer / éteindre",
            font=("Arial", 12, "bold")
        )
        title.pack(pady=(0, 10))

        grid_frame = tk.Frame(main_frame, bg=GRID_BG, bd=2, relief="groove")
        grid_frame.pack()

        for row in range(GRID_SIZE):
            cell_row = []
            for col in range(GRID_SIZE):
                canvas = tk.Canvas(
                    grid_frame,
                    width=CELL_SIZE,
                    height=CELL_SIZE,
                    bg=GRID_BG,
                    highlightthickness=0
                )
                canvas.grid(row=row, column=col, padx=1, pady=1)

                rect = canvas.create_rectangle(
                    CELL_PADDING,
                    CELL_PADDING,
                    CELL_SIZE - CELL_PADDING,
                    CELL_SIZE - CELL_PADDING,
                    fill=OFF_COLOR,
                    outline="#555555",
                    width=2
                )

                canvas.bind(
                    "<Button-1>",
                    lambda event, r=row, c=col: self.toggle_cell(r, c)
                )

                cell_row.append((canvas, rect))
            self.cells.append(cell_row)

        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(pady=12)

        clear_btn = tk.Button(
            buttons_frame,
            text="Effacer",
            width=12,
            command=self.clear_grid
        )
        clear_btn.pack(side="left", padx=5)

        ok_btn = tk.Button(
            buttons_frame,
            text="OK",
            width=12,
            command=self.export_code
        )
        ok_btn.pack(side="left", padx=5)

        self.output_label = tk.Label(
            main_frame,
            text="Code généré :",
            anchor="w",
            font=("Arial", 10, "bold")
        )
        self.output_label.pack(fill="x", pady=(10, 4))

        self.output_text = tk.Text(
            main_frame,
            width=40,
            height=14,
            font=("Courier New", 11)
        )
        self.output_text.pack()

        copy_btn = tk.Button(
            main_frame,
            text="Copier dans le presse-papiers",
            command=self.copy_output
        )
        copy_btn.pack(pady=(8, 0))

    def toggle_cell(self, row, col):
        self.grid[row][col] = 0 if self.grid[row][col] else 1
        self.refresh_cell(row, col)

    def refresh_cell(self, row, col):
        canvas, rect = self.cells[row][col]
        color = ON_COLOR if self.grid[row][col] else OFF_COLOR
        canvas.itemconfig(rect, fill=color)

    def clear_grid(self):
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                self.grid[row][col] = 0
                self.refresh_cell(row, col)
        self.output_text.delete("1.0", tk.END)

    def row_to_binary(self, row_values):
        """
        Compensation de la matrice réelle :
        - la matrice décale les colonnes d'1 vers la gauche
        - on compense en exportant d'1 vers la droite

        Si l'éditeur contient :
        c0 c1 c2 c3 c4 c5 c6 c7

        on exporte :
        c7 c0 c1 c2 c3 c4 c5 c6
        """
        c0, c1, c2, c3, c4, c5, c6, c7 = row_values
        return f"B{c7}{c0}{c1}{c2}{c3}{c4}{c5}{c6}"

    def export_code(self):
        name = simpledialog.askstring("Nom", "Nom du motif :")
        if not name:
            return

        # Compensation verticale :
        # la matrice inverse les lignes haut/bas
        lines = []
        for row in range(7, -1, -1):
            lines.append(self.row_to_binary(self.grid[row]))

        result = f"{name}[] =\n{{ " + ",\n  ".join(lines) + "\n};"

        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", result)

        messagebox.showinfo("Terminé", "Code généré.")

    def copy_output(self):
        content = self.output_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Vide", "Aucun code à copier.")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update()
        messagebox.showinfo("Copié", "Le code a été copié dans le presse-papiers.")


if __name__ == "__main__":
    root = tk.Tk()
    app = LedMatrixEditor(root)
    root.mainloop()