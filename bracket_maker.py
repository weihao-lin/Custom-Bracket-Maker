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
        self.initial_names: List[str] = []

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
        self.initial_names = [n.strip() for n in names if n.strip()]

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
            for i in range(2 * (rounds_count - 1)):
                cnt = max(1, bracket_size // (2 ** ((i // 2) + 2)))
                self.losers_rounds.append(RoundData(f"Losers R{i+1}", [Match(None, None) for _ in range(cnt)]))
            self.losers_rounds.append(RoundData("Losers Final", [Match(None, None)]))

    def current_round(self) -> RoundData:
        return self.rounds[self.current_round_idx]

    def set_winner(self, round_idx: int, match_idx: int, winner_slot: int):
        match = self.rounds[round_idx].matches[match_idx]
        winner = match.p1 if winner_slot == 1 else match.p2
        if winner is None:
            return
        match.winner = winner
        self._recompute_all_rounds()

    def _recompute_all_rounds(self):
        for r_idx in range(1, len(self.rounds)):
            prev_winners = [m.winner for m in self.rounds[r_idx - 1].matches]
            for i, m in enumerate(self.rounds[r_idx].matches):
                m.p1 = prev_winners[2 * i] if 2 * i < len(prev_winners) else None
                m.p2 = prev_winners[2 * i + 1] if 2 * i + 1 < len(prev_winners) else None
                if m.winner not in (m.p1, m.p2):
                    m.winner = None
                if m.p1 and not m.p2:
                    m.winner = m.p1
                elif m.p2 and not m.p1:
                    m.winner = m.p2

        self.current_round_idx = self._first_unfinished_winners_round()
        self.finished = bool(self.rounds and self.rounds[-1].matches and self.rounds[-1].matches[0].winner)
        if self.mode == "double":
            self._recompute_losers_rounds()

    def _first_unfinished_winners_round(self) -> int:
        for i, rnd in enumerate(self.rounds):
            if any((m.p1 or m.p2) and m.winner is None for m in rnd.matches):
                return i
        return max(0, len(self.rounds) - 1)

    def _recompute_losers_rounds(self):
        for rnd in self.losers_rounds:
            for m in rnd.matches:
                m.p1 = None
                m.p2 = None
                m.winner = None

        wb_losers: List[List[Participant]] = []
        for rnd in self.rounds:
            losers = []
            for m in rnd.matches:
                if m.winner and m.p1 and m.p2:
                    losers.append(m.p2 if m.winner == m.p1 else m.p1)
            wb_losers.append(losers)

        lb_prev_winners: List[Participant] = []
        for i, lb_round in enumerate(self.losers_rounds[:-1]):
            entrants = []
            if i == 0:
                entrants.extend(wb_losers[0] if wb_losers else [])
            elif i % 2 == 0:
                wb_idx = min((i // 2) + 1, len(wb_losers) - 1)
                entrants.extend(lb_prev_winners)
                entrants.extend(wb_losers[wb_idx] if wb_idx >= 0 else [])
            else:
                entrants.extend(lb_prev_winners)

            lb_prev_winners = []
            for m_idx, m in enumerate(lb_round.matches):
                m.p1 = entrants[2 * m_idx] if 2 * m_idx < len(entrants) else None
                m.p2 = entrants[2 * m_idx + 1] if 2 * m_idx + 1 < len(entrants) else None
                if m.winner not in (m.p1, m.p2):
                    m.winner = None
                if m.p1 and not m.p2:
                    m.winner = m.p1
                elif m.p2 and not m.p1:
                    m.winner = m.p2
                if m.winner:
                    lb_prev_winners.append(m.winner)

        if self.losers_rounds:
            grand = self.losers_rounds[-1].matches[0]
            wb_final_loser = None
            if self.rounds and self.rounds[-1].matches:
                final = self.rounds[-1].matches[0]
                if final.winner and final.p1 and final.p2:
                    wb_final_loser = final.p2 if final.winner == final.p1 else final.p1
            grand.p1 = lb_prev_winners[0] if lb_prev_winners else None
            grand.p2 = wb_final_loser

    def randomize_current_round(self):
        participants = [Participant(n) for n in self.initial_names]
        random.shuffle(participants)
        size = len(self.rounds[0].matches) * 2
        participants += [None] * (size - len(participants))
        random.shuffle(participants)
        for i, m in enumerate(self.rounds[0].matches):
            m.p1 = participants[2 * i]
            m.p2 = participants[2 * i + 1]
            m.winner = None
            if m.p1 and not m.p2:
                m.winner = m.p1
            elif m.p2 and not m.p1:
                m.winner = m.p2
        self._recompute_all_rounds()

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
        ttk.Button(control, text="Save Finished Bracket", command=self.save_finished).grid(row=8, column=0, sticky="ew", pady=4)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(control, textvariable=self.status_var, wraplength=220).grid(row=9, column=0, sticky="ew", pady=(10, 0))

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

                ttk.Label(card, text=m.display_label(), width=32, foreground="#005bbb", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")

                is_active = (r_idx == current)
                p1_enabled = is_active and m.p1 is not None
                p2_enabled = is_active and m.p2 is not None

                p1_text = m.p1.name if m.p1 else "TBD"
                p2_text = m.p2.name if m.p2 else "TBD"
                b1 = tk.Button(card, text=p1_text, command=lambda rr=r_idx, mm=m_idx: self.pick(rr, mm, 1), state=("normal" if p1_enabled else "disabled"))
                b2 = tk.Button(card, text=p2_text, command=lambda rr=r_idx, mm=m_idx: self.pick(rr, mm, 2), state=("normal" if p2_enabled else "disabled"))
                if m.winner == m.p1 and m.p1:
                    b1.configure(bg="#c8f7c5")
                if m.winner == m.p2 and m.p2:
                    b2.configure(bg="#c8f7c5")
                b1.grid(row=1, column=0, sticky="ew", pady=(4, 0))
                b2.grid(row=1, column=1, sticky="ew", pady=(4, 0))

                if self.engine.best_of_enabled:
                    ttk.Label(card, text="Score note:").grid(row=2, column=0, sticky="w", pady=(6, 0))
                    s1 = tk.StringVar(value=m.score1)
                    s2 = tk.StringVar(value=m.score2)
                    e1 = ttk.Entry(card, width=5, textvariable=s1)
                    e2 = ttk.Entry(card, width=5, textvariable=s2)
                    e1.grid(row=2, column=0, sticky="e", padx=(0, 28))
                    e2.grid(row=2, column=1, sticky="w")
                    self.score_entries.append((s1, s2, r_idx, m_idx))

        if self.engine.mode == "double" and self.engine.losers_rounds:
            losers_col_start = len(self.engine.rounds)
            for li, rnd in enumerate(self.engine.losers_rounds):
                col = ttk.LabelFrame(self.inner, text=rnd.name)
                col.grid(row=2, column=li, sticky="n", padx=12, pady=8)
                for m_idx, m in enumerate(rnd.matches):
                    card = ttk.Frame(col, relief="solid", borderwidth=1, padding=8)
                    card.grid(row=m_idx, column=0, sticky="ew", pady=6)
                    ttk.Label(card, text=m.display_label(), width=28, foreground="#7a1f7a").grid(row=0, column=0, sticky="w")

    def pick(self, round_idx: int, match_idx: int, side: int):
        self._store_scores()
        self.engine.set_winner(round_idx, match_idx, side)
        self.render()

    def _store_scores(self):
        for s1, s2, r, m in self.score_entries:
            self.engine.rounds[r].matches[m].score1 = s1.get()
            self.engine.rounds[r].matches[m].score2 = s2.get()

    def randomize_current(self):
        if not self.engine.rounds:
            messagebox.showwarning("No bracket", "Create a bracket first.")
            return
        round_name = self.engine.rounds[0].name
        confirmed = messagebox.askyesno("Confirm randomize", f"Randomize first-round seeding? This resets the bracket.")
        if not confirmed:
            return
        self._store_scores()
        self.engine.randomize_current_round()
        self.status_var.set(f"Randomized seeding for {round_name} and reset downstream rounds.")
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

if __name__ == "__main__":
    app = BracketApp()
    app.mainloop()
