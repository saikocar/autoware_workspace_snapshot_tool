#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import simpledialog

from watchfiles import watch, DefaultFilter


def get_git_author(cwd: Path = None) -> dict | None:
    name = subprocess.run(['git', 'config', 'user.name'], capture_output=True, cwd=cwd, text=True).stdout.strip()
    email = subprocess.run(['git', 'config', 'user.email'], capture_output=True, cwd=cwd, text=True).stdout.strip()
    return {'author': f'{name} <{email}>', 'name': name, 'email': email} if name and email and email != '<>' else None


def parse_git_author(author: str) -> tuple[str | None, str | None]:
    splitted = author.split(' <')
    if len(splitted) == 2 and splitted[0].strip() != '' and splitted[1].endswith('>'):
        name = splitted[0].strip()
        email = splitted[1][:-1]
        return (name, email if email else '<>')
    return (None, None)


def setup_repo_for_snapshot(workspace_path: Path) -> None:
    if (workspace_path / '.git' / '3134559c-8a45-4d8a-a037-71835eedc5d8').exists():
        return

    if not (workspace_path / '.git').exists():
        logging.info('This workspace is not a Git repository, so we will set that up')
        subprocess.run(['git', 'init'], cwd=workspace_path)

    user_info = get_git_author(workspace_path)
    subprocess.run(['git', 'config', '--local', 'user.name', user_info['name'] if user_info else 'autoware_workspace_snapshot_tool'], cwd=workspace_path)
    subprocess.run(['git', 'config', '--local', 'user.email', user_info['email'] if user_info else '<>'], cwd=workspace_path)

    if not (workspace_path / '.gitignore').exists():
        with open(workspace_path / '.gitignore', 'w') as f:
            f.writelines(['.vscode/\n', 'build/\n', 'install/\n', 'log/\n', '__pycache__/\n'])
        subprocess.run(['git', 'add', '.gitignore'], cwd=workspace_path)
        subprocess.run(['git', 'commit', '-m', 'Create `.gitignore` for snapshots'], cwd=workspace_path)
    else:
        logging.debug('.gitignore found, this workspace might be a meta-repository')
        with open(workspace_path / '.gitignore', 'r') as f:
            gitignore_lines = f.readlines()
        with open(workspace_path / '.gitignore', 'w') as f:
            for line in gitignore_lines:
                if line.strip() == '/src/' or line.strip() == 'src/' or line.strip() == 'src':
                    logging.info('src directory is ignored, comment out to make it trackable')
                    line = f'# {line}'
                f.write(line)
        subprocess.run(['git', 'add', '.gitignore'], cwd=workspace_path)
        subprocess.run(['git', 'commit', '-m', 'Remove src directory from `.gitignore`'], cwd=workspace_path)

    take_workspace_snapshot(workspace_path, 'First snapshot of initialization')

    (workspace_path / '.git' / '3134559c-8a45-4d8a-a037-71835eedc5d8').touch()


def take_workspace_snapshot(workspace_path: Path, reason: str | None = None, author: str | None = None) -> None:
    revert_directory_list = []
    for dot_git in (workspace_path / 'src').rglob('.git'):
        if not dot_git.is_dir():
            continue
        with open(dot_git / '.gitignore', 'w') as f:
            f.write('*')
        renamed_path = dot_git.rename(dot_git.parent / '.8a448599-fc3f-4bb8-be33-86b136748c80')
        revert_directory_list.append(renamed_path)

    subprocess.run(['git', 'add', '.'], cwd=workspace_path)

    for git_directory in revert_directory_list:
        (git_directory / '.gitignore').unlink()
        git_directory.rename(git_directory.parent / '.git')

    subprocess.run(['git', 'commit', '-m', f'Snapshot taken: {reason if reason else "No reasons provided"}'] + (['--author', author] if author else []), cwd=workspace_path)

    remote_url = subprocess.run(['git', 'config', 'remote.origin.url'], capture_output=True, cwd=workspace_path, text=True).stdout.strip()
    if remote_url and not ('autowarefoundation/autoware' in remote_url):
        subprocess.run(['git', 'push'], cwd=workspace_path)


def revert_renamed_git_dirs(workspace_path: Path) -> None:
    for renamed_git in (workspace_path / 'src').rglob('.8a448599-fc3f-4bb8-be33-86b136748c80'):
        if renamed_git.is_dir():
            logging.warning(f'Reverting renamed .git directory at {renamed_git}')
            (renamed_git.parent / '.git').rename(renamed_git)


def main() -> None:
    if not sys.argv[1]:
        logging.error('Please provide an Autoware workspace path')
        return

    try:
        workspace_path = Path(sys.argv[1]).expanduser().resolve(strict=True)
    except FileNotFoundError:
        logging.error(f'{sys.argv[1]} does not exist')
        return

    if not (workspace_path / 'src' / 'universe').exists():
        logging.error(f'{sys.argv[1]} is not an Autoware workspace')
        return

    setup_repo_for_snapshot(workspace_path)
    revert_renamed_git_dirs(workspace_path)  # リネームされた git ディレクトリがそのまま残っていることがあるので起動時に戻す
    take_workspace_snapshot(workspace_path, 'Autostart snapshot')

    class MyFilter(DefaultFilter):
        def __init__(self):
            super().__init__(ignore_dirs=super().ignore_dirs + ('build', 'install', 'log', '.8a448599-fc3f-4bb8-be33-86b136748c80'))

    next_ask_time = datetime.now() + timedelta(minutes=10)
    for changes in watch(workspace_path, watch_filter=MyFilter()):
        if datetime.now() <= next_ask_time:
            logging.info(f'Too early to ask for a snapshot (remains {next_ask_time - datetime.now()})')
            continue

        input_reason = input_author = parsed_name = parsed_email = ''
        dialog_state = 1
        while dialog_state:
            if dialog_state == 1:
                input_reason = simpledialog.askstring('スナップショットをとりますか？', 'Autoware ワークスペースの変更を検出しました。\n変更内容を下記に入力してください。', initialvalue=input_reason)
                dialog_state = 2 if input_reason is not None else 0
            elif dialog_state == 2:
                author_placeholder = input_author if input_author else (get_git_author(workspace_path)['author'] if get_git_author(workspace_path) else 'Your Name <you@example.com>')
                input_author = simpledialog.askstring('あなたは誰ですか？', 'コミットを行う際の、あなたの名前とメールアドレスを入力してください。', initialvalue=author_placeholder)
                if input_author is None:
                    dialog_state = 1
                else:
                    (parsed_name, parsed_email) = parse_git_author(input_author)
                    dialog_state = 0 if parsed_name and parsed_email else 2

        next_ask_time = datetime.now() + timedelta(minutes=10)

        if not parsed_name or not parsed_email:
            logging.info('User canceled the snapshot dialog')
            continue

        logging.debug(f'Parsed name: {parsed_name}, Parsed email: {parsed_email}')
        subprocess.run(['git', 'config', '--local', 'user.name', parsed_name], cwd=workspace_path)
        subprocess.run(['git', 'config', '--local', 'user.email', parsed_email], cwd=workspace_path)

        take_workspace_snapshot(workspace_path, input_reason)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s')
    logging.getLogger().setLevel(logging.INFO)
    main()
