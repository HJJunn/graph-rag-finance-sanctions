class ConversationMemory:
    def __init__(self, max_turns=6):
        self.max_turns = max_turns
        self.turns = []
        self.summary = ""

    def add_turn(self, user, assistant):
        self.turns.append({"user": user, "assistant": assistant})

        if len(self.turns) > self.max_turns:
            oldest = self.turns.pop(0)

            self.summary += f"\n사용자: {oldest['user']}\n어시스턴트: {oldest['assistant']}"

    def build_history_text(self):
        text = ""

        if self.summary:
            text += "[요약된 이전 대화]\n"
            text += self.summary + "\n"

        if self.turns:
            text += "\n[최근 대화]\n"
            for t in self.turns:
                text += f"사용자: {t['user']}\n"
                text += f"어시스턴트: {t['assistant']}\n"

        return text.strip()