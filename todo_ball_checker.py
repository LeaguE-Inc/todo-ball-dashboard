#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ボール管理型TODO リスト - 自動期限チェック＆リマインドスクリプト
毎朝8時に実行して、対応期限を超えたタスクを自動でリマインド化する
"""

import re
import shutil
from datetime import datetime, date
from pathlib import Path

TODO_FILE = Path.home() / "AppData/Roaming/Claude/local-agent-mode-sessions/3c6b9918-eab0-4c57-af5d-b217014a31de/4b196c72-d7b2-4def-9004-f3779e5b6581/local_09443a3c-0803-4582-a425-3bf352e8c61f/outputs/TODO_BALL_FORMAT.md"

class TodoBallChecker:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.content = ""
        self.reminders = []

    def load_file(self):
        """マークダウンファイルを読み込む"""
        if not self.file_path.exists():
            print(f"❌ ファイルが見つかりません: {self.file_path}")
            return False

        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        print(f"✅ ファイル読み込み完了: {self.file_path.name}")
        return True

    def parse_waiting_tasks(self):
        """対応待ちセクションからタスクをパース"""
        waiting_section = self._extract_section("## ⏳ 対応待ち")
        if not waiting_section:
            print("⚠️ 対応待ちセクションが見つかりません")
            return []

        tasks = []
        task_pattern = r'- \[ \] \[(期限: (\d{4}-\d{2}-\d{2}))\](.+?)(?=\n  - ボール:|$)'

        for match in re.finditer(task_pattern, waiting_section):
            deadline_text = match.group(2)
            task_name = match.group(3).strip()

            ball_start = match.end()
            ball_match = re.search(r'- ボール: ([^\n]+)', waiting_section[ball_start:])
            ball_owner = ball_match.group(1).strip() if ball_match else "不明"

            tasks.append({
                'deadline': deadline_text,
                'name': task_name,
                'ball_owner': ball_owner,
                'full_match': match.group(0)
            })

        return tasks

    def check_overdue_tasks(self):
        """期限超過したタスクをチェック"""
        tasks = self.parse_waiting_tasks()
        today = date.today()
        overdue = []

        for task in tasks:
            try:
                deadline = datetime.strptime(task['deadline'], '%Y-%m-%d').date()
                if deadline < today:
                    days_overdue = (today - deadline).days
                    overdue.append({
                        **task,
                        'days_overdue': days_overdue
                    })
            except ValueError:
                print(f"⚠️ 日付フォーマットエラー: {task['deadline']}")

        return overdue

    def create_reminder_tasks(self, overdue_tasks):
        """リマインドタスクを生成"""
        reminders = []
        for task in overdue_tasks:
            reminder = f"""- [ ] 【リマインド】{task['name']}（{task['days_overdue']}日遅延）
  - ボール: {task['ball_owner']}
  - 元期限: {task['deadline']}
  - 対応: この相手に催促連絡を入れてください"""
            reminders.append(reminder)
        return reminders

    def _extract_section(self, section_header):
        """指定したセクションの内容を抽出"""
        pattern = f"{section_header}(.*?)(?=\n## |$)"
        match = re.search(pattern, self.content, re.DOTALL)
        return match.group(1) if match else None

    def update_reminders_section(self, new_reminders):
        """リマインドセクションを更新"""
        if not new_reminders:
            return self.content

        reminder_section_pattern = r'(## 📢 リマインド（対応期限超過）\n\n⚠️ \*\*以下は自動生成されます。毎朝8時にスクリプトが実行されます。\*\*\n)(.*?)(?=\n## |---|\n\n## ✅)'

        reminder_items = "\n".join(new_reminders) + "\n\n"

        updated_content = re.sub(
            reminder_section_pattern,
            r'\1' + reminder_items,
            self.content,
            flags=re.DOTALL
        )

        return updated_content

    def update_timestamp(self, content):
        """ファイルの最終更新タイムスタンプを更新"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        updated = re.sub(
            r'\*\*最終更新\*\*: .+?  \n',
            f'**最終更新**: {now}  \n',
            content
        )
        return updated

    def save_file(self, content):
        """ファイルを保存（バックアップ付き）"""
        backup_file = self.file_path.parent / f"{self.file_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        shutil.copy2(self.file_path, backup_file)
        print(f"💾 バックアップ作成: {backup_file.name}")

        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ ファイル更新完了: {self.file_path.name}")

    def run(self):
        """メイン処理を実行"""
        print("\n" + "="*60)
        print("🤖 ボール管理TODO - 自動期限チェック開始")
        print(f"📅 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")

        if not self.load_file():
            return False

        overdue_tasks = self.check_overdue_tasks()

        if not overdue_tasks:
            print("✅ 期限超過タスクはありません。素晴らしい！")
            return True

        print(f"\n⚠️ 期限超過タスク: {len(overdue_tasks)}件\n")
        for task in overdue_tasks:
            print(f"  • {task['name']}")
            print(f"    期限: {task['deadline']} ({task['days_overdue']}日遅延)")
            print(f"    待機先: {task['ball_owner']}")
            print()

        reminder_tasks = self.create_reminder_tasks(overdue_tasks)

        updated_content = self.update_reminders_section(reminder_tasks)

        updated_content = self.update_timestamp(updated_content)

        self.save_file(updated_content)

        print(f"\n{'='*60}")
        print(f"✨ リマインド {len(reminder_tasks)} 件を生成して保存しました")
        print(f"{'='*60}\n")

        return True


if __name__ == "__main__":
    checker = TodoBallChecker(TODO_FILE)
    checker.run()