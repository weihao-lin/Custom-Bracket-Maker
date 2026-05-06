import json
import math
import random
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

MAX_ENTRIES = 512


@dataclass
class Participant:
    name: str


@dataclass
class Match:
    p1: Optional[Participant]
    p2: Optional[Participant]
    winner: Optional[Participant] = None
    score1: str = ""
    score2: str = ""

    def display_label(self) -> str:
        n1 = self.p1.name if self.p1 else "BYE"
        n2 = self.p2.name if self.p2 else "BYE"
        return f"{n1} vs {n2}"


@dataclass
class RoundData:
    name: str
    matches: List[Match] = field(default_factory=list)


class BracketEngine:
    def __init__(self):
        self.title = ""
        self.mode = "regular"  # regular | double
        self.best_of_enabled = False
        self.best_of_n = 3
        self.rounds: List[RoundData] = []
        self.current_round_idx = 0
        self.finished = False

        # double elimination data
        self.losers_rounds: List[RoundData] = []

    @staticmethod
    def _next_power_of_two(n: int) -> int:
        return 1 if n <= 1 else 2 ** math.ceil(math.log2(n))

    def start(self, title: str, names: List[str], mode: str, best_of_enabled: bool, best_of_n: int):
        self.title = title.strip() or "Untitled Bracket"
        self.mode = mode
        self.best_of_enabled = best_of_enabled
        self.best_of_n = best_of_n
        self.current_round_idx = 0
        self.finished = False
        self.rounds = []
        self.losers_rounds = []

        participants = [Participant(n.strip()) for n in names if n.strip()]
        random.shuffle(participants)

        bracket_size = self._next_power_of_two(len(participants))
        byes_needed = bracket_size - len(participants)
        slots = participants + [None] * byes_needed
        random.shuffle(slots)

        matches = []
        for i in range(0, len(slots), 2):
            p1 = slots[i]
            p2 = slots[i + 1]
            m = Match(p1, p2)
            if p1 and not p2:
                m.winner = p1
            elif p2 and not p1:
                m.winner = p2
            matches.append(m)

        self.rounds.append(RoundData("Round 1", matches))
        self._grow_empty_rounds(bracket_size)

    def _grow_empty_rounds(self, bracket_size: int):
        rounds_count = int(math.log2(bracket_size))
        for r in range(2, rounds_count + 1):
            match_count = bracket_size // (2**r)
            self.rounds.append(RoundData(f"Round {r}", [Match(None, None) for _ in range(match_count)]))

        if self.mode == "double":
            # Simplified losers bracket structure for extensibility.
            losers_round_count = max(1, rounds_count - 1)
            for r in range(1, losers_round_count + 1):
                cnt = max(1, bracket_size // (2 ** (r + 1)))
                self.losers_rounds.append(RoundData(f"Losers R{r}", [Match(None, None) for _ in range(cnt)]))

    def current_round(self) -> RoundData:
        return self.rounds[self.current_round_idx]

    def set_winner(self, round_idx: int, match_idx: int, winner_slot: int):
        match = self.rounds[round_idx].matches[match_idx]
        winner = match.p1 if winner_slot == 1 else match.p2
        if winner is None:
            return
        match.winner = winner

        if self.mode == "double":
            loser = match.p2 if winner_slot == 1 else match.p1
            if loser:
                self._drop_to_losers(round_idx, loser)

    def _drop_to_losers(self, winners_round_idx: int, loser: Participant):
        if not self.losers_rounds:
            return
        target = min(winners_round_idx, len(self.losers_rounds) - 1)
        for m in self.losers_rounds[target].matches:
            if m.p1 is None:
                m.p1 = loser
                return
            if m.p2 is None:
                m.p2 = loser
                return

    def advance_round(self):
        if self.finished:
            return
        if self.current_round_idx >= len(self.rounds) - 1:
            self.finished = True
            return

        current = self.rounds[self.current_round_idx]
        next_round = self.rounds[self.current_round_idx + 1]

        winners = [m.winner for m in current.matches if m.winner is not None]
        for m in next_round.matches:
            m.p1 = None
            m.p2 = None
            m.winner = None

        for i, winner in enumerate(winners):
            target = next_round.matches[i // 2]
            if i % 2 == 0:
                target.p1 = winner
            else:
                target.p2 = winner

        for m in next_round.matches:
            if m.p1 and not m.p2:
                m.winner = m.p1
            elif m.p2 and not m.p1:
                m.winner = m.p2

        self.current_round_idx += 1
        if self.current_round_idx == len(self.rounds) - 1:
            final_round = self.rounds[self.current_round_idx]
            if len(final_round.matches) == 1 and final_round.matches[0].winner:
                self.finished = True

    def randomize_current_round(self):
        r = self.current_round()
        pool = []
        for m in r.matches:
            if m.p1:
                pool.append(m.p1)
            if m.p2:
                pool.append(m.p2)
            m.winner = None
        random.shuffle(pool)
        while len(pool) < len(r.matches) * 2:
            pool.append(None)

        for i, m in enumerate(r.matches):
            m.p1 = pool[2 * i]
            m.p2 = pool[2 * i + 1]
            if m.p1 and not m.p2:
                m.winner = m.p1
            elif m.p2 and not m.p1:
                m.winner = m.p2

    def export_json(self) -> dict:
        return {
            "title": self.title,
            "mode": self.mode,
            "best_of_enabled": self.best_of_enabled,
            "best_of_n": self.best_of_n,
            "current_round_idx": self.current_round_idx,
            "finished": self.finished,
            "rounds": [
                {
                    "name": rnd.name,
                    "matches": [
                        {
                            "p1": m.p1.name if m.p1 else None,
                            "p2": m.p2.name if m.p2 else None,
                            "winner": m.winner.name if m.winner else None,
                            "score1": m.score1,
                            "score2": m.score2,
                        }
                        for m in rnd.matches
                    ],
                }
                for rnd in self.rounds
            ],
        }


class BracketApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Custom Bracket Maker")
        self.geometry("1280x760")

        self.engine = BracketEngine()
        self.score_entries = []

        self._build_layout()

    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        control = ttk.Frame(self, padding=10)
        control.grid(row=0, column=0, sticky="ns")
        control.columnconfigure(0, weight=1)

        ttk.Label(control, text="Bracket Title").grid(row=0, column=0, sticky="w")
        self.title_var = tk.StringVar(value="My Bracket")
        ttk.Entry(control, textvariable=self.title_var, width=28).grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(control, text="Participants (one per line)").grid(row=2, column=0, sticky="w")
        self.participants_txt = tk.Text(control, width=30, height=18, wrap="none")
        self.participants_txt.grid(row=3, column=0, sticky="nsew")

        self.mode_var = tk.StringVar(value="regular")
        mode_frame = ttk.LabelFrame(control, text="Bracket Add-ons")
        mode_frame.grid(row=4, column=0, sticky="ew", pady=10)
        ttk.Radiobutton(mode_frame, text="Regular (base)", value="regular", variable=self.mode_var).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(mode_frame, text="Double elimination", value="double", variable=self.mode_var).grid(row=1, column=0, sticky="w")

        self.bestof_enabled_var = tk.BooleanVar(value=False)
        self.bestof_n_var = tk.IntVar(value=3)
        bestof_frame = ttk.LabelFrame(control, text="Best-of Add-on")
        bestof_frame.grid(row=5, column=0, sticky="ew")
        ttk.Checkbutton(bestof_frame, text="Enable Best-of", variable=self.bestof_enabled_var).grid(row=0, column=0, sticky="w")
        ttk.Label(bestof_frame, text="Series length").grid(row=1, column=0, sticky="w")
        ttk.Combobox(bestof_frame, values=[3, 5, 7], state="readonly", textvariable=self.bestof_n_var, width=8).grid(row=2, column=0, sticky="w")

        ttk.Button(control, text="Create Bracket", command=self.create_bracket).grid(row=6, column=0, sticky="ew", pady=(12, 4))
        ttk.Button(control, text="Randomize Seeding", command=self.randomize_current).grid(row=7, column=0, sticky="ew", pady=4)
        ttk.Button(control, text="Advance Round", command=self.advance_round).grid(row=8, column=0, sticky="ew", pady=4)
        ttk.Button(control, text="Save Finished Bracket", command=self.save_finished).grid(row=9, column=0, sticky="ew", pady=4)
        ttk.Button(control, text="Save Options Help", command=self.show_save_suggestions).grid(row=10, column=0, sticky="ew", pady=4)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(control, textvariable=self.status_var, wraplength=220).grid(row=11, column=0, sticky="ew", pady=(10, 0))

        board = ttk.Frame(self, padding=6)
        board.grid(row=0, column=1, sticky="nsew")
        board.rowconfigure(0, weight=1)
        board.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(board, bg="#f8f8f8")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        xscroll = ttk.Scrollbar(board, orient="horizontal", command=self.canvas.xview)
        yscroll = ttk.Scrollbar(board, orient="vertical", command=self.canvas.yview)
        xscroll.grid(row=1, column=0, sticky="ew")
        yscroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)

        self.inner = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=max(event.width, 920))

    def parse_names(self) -> List[str]:
        raw = self.participants_txt.get("1.0", "end").splitlines()
        names = [r.strip() for r in raw if r.strip()]
        if len(names) < 2:
            raise ValueError("Need at least 2 entries.")
        if len(names) > MAX_ENTRIES:
            raise ValueError(f"Maximum entries is {MAX_ENTRIES}.")
        return names

    def create_bracket(self):
        try:
            names = self.parse_names()
        except ValueError as e:
            messagebox.showerror("Invalid entries", str(e))
            return

        self.engine.start(
            self.title_var.get(),
            names,
            self.mode_var.get(),
            self.bestof_enabled_var.get(),
            self.bestof_n_var.get(),
        )
        self.status_var.set(f"Created bracket with {len(names)} entries.")
        self.render()

    def render(self):
        for child in self.inner.winfo_children():
            child.destroy()

        title = f"{self.engine.title} | Mode: {self.engine.mode}"
        if self.engine.best_of_enabled:
            title += f" | Best-of-{self.engine.best_of_n}"
        ttk.Label(self.inner, text=title, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=10)

        current = self.engine.current_round_idx
        self.score_entries = []

        for r_idx, rnd in enumerate(self.engine.rounds):
            col = ttk.LabelFrame(self.inner, text=rnd.name)
            col.grid(row=1, column=r_idx, sticky="n", padx=12, pady=8)

            for m_idx, m in enumerate(rnd.matches):
                card = ttk.Frame(col, relief="solid", borderwidth=1, padding=8)
                card.grid(row=m_idx, column=0, sticky="ew", pady=6)

                ttk.Label(card, text=m.display_label(), width=32).grid(row=0, column=0, columnspan=2, sticky="w")
                winner = m.winner.name if m.winner else "(none)"
                ttk.Label(card, text=f"Winner: {winner}").grid(row=1, column=0, columnspan=2, sticky="w")

                is_active = (r_idx == current)
                p1_enabled = is_active and m.p1 is not None
                p2_enabled = is_active and m.p2 is not None

                ttk.Button(card, text="Pick P1", command=lambda rr=r_idx, mm=m_idx: self.pick(rr, mm, 1), state=("normal" if p1_enabled else "disabled")).grid(row=2, column=0, sticky="ew", pady=(4, 0))
                ttk.Button(card, text="Pick P2", command=lambda rr=r_idx, mm=m_idx: self.pick(rr, mm, 2), state=("normal" if p2_enabled else "disabled")).grid(row=2, column=1, sticky="ew", pady=(4, 0))

                if self.engine.best_of_enabled:
                    ttk.Label(card, text="Score note:").grid(row=3, column=0, sticky="w", pady=(6, 0))
                    s1 = tk.StringVar(value=m.score1)
                    s2 = tk.StringVar(value=m.score2)
                    e1 = ttk.Entry(card, width=5, textvariable=s1)
                    e2 = ttk.Entry(card, width=5, textvariable=s2)
                    e1.grid(row=3, column=0, sticky="e", padx=(0, 28))
                    e2.grid(row=3, column=1, sticky="w")
                    self.score_entries.append((s1, s2, r_idx, m_idx))

        if self.engine.mode == "double" and self.engine.losers_rounds:
            losers_col_start = len(self.engine.rounds)
            for li, rnd in enumerate(self.engine.losers_rounds):
                col = ttk.LabelFrame(self.inner, text=rnd.name)
                col.grid(row=1, column=losers_col_start + li, sticky="n", padx=12, pady=8)
                for m_idx, m in enumerate(rnd.matches):
                    card = ttk.Frame(col, relief="solid", borderwidth=1, padding=8)
                    card.grid(row=m_idx, column=0, sticky="ew", pady=6)
                    ttk.Label(card, text=m.display_label(), width=28).grid(row=0, column=0, sticky="w")

    def pick(self, round_idx: int, match_idx: int, side: int):
        self._store_scores()
        self.engine.set_winner(round_idx, match_idx, side)
        self.render()

    def _store_scores(self):
        for s1, s2, r, m in self.score_entries:
            self.engine.rounds[r].matches[m].score1 = s1.get()
            self.engine.rounds[r].matches[m].score2 = s2.get()

    def advance_round(self):
        self._store_scores()
        self.engine.advance_round()
        self.render()
        if self.engine.finished:
            messagebox.showinfo("Completed", "Bracket is finished. You can now save it.")
            self.status_var.set("Bracket finished.")
        else:
            self.status_var.set(f"Advanced to round {self.engine.current_round_idx + 1}.")

    def randomize_current(self):
        if not self.engine.rounds:
            messagebox.showwarning("No bracket", "Create a bracket first.")
            return
        round_name = self.engine.current_round().name
        confirmed = messagebox.askyesno("Confirm randomize", f"Randomize matchups for {round_name}? This clears current winner picks in that round.")
        if not confirmed:
            return
        self._store_scores()
        self.engine.randomize_current_round()
        self.status_var.set(f"Randomized seeding for {round_name}.")
        self.render()

    def save_finished(self):
        if not self.engine.rounds:
            messagebox.showwarning("No bracket", "Create and complete a bracket first.")
            return
        if not self.engine.finished:
            messagebox.showwarning("Not finished", "Finish the bracket before saving.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.engine.title.replace(' ', '_').lower()}_bracket.json",
        )
        if not path:
            return
        self._store_scores()
        data = self.engine.export_json()
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        messagebox.showinfo("Saved", f"Saved bracket to:\n{path}")

    def show_save_suggestions(self):
        messagebox.showinfo(
            "Save format suggestions",
            "Recommended primary format: JSON (preserves structure + winners + score notes).\n\n"
            "Other useful exports to add later:\n"
            "• PDF: best for printing/sharing static finished bracket.\n"
            "• PNG/SVG image: quick visual sharing, no editability.\n"
            "• HTML export: viewable in browser with structure retained.\n\n"
            "For now, JSON is implemented because it is easiest to reload/extend safely.",
        )


if __name__ == "__main__":
    app = BracketApp()
    app.mainloop()
