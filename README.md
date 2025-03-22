# autoware_workspace_snapshot_tool

A tool (which may be useful to a few people) that takes a snapshot of the entire Autoware workspace using git commits

## Installation

```bash
git clone https://github.com/saikocar/autoware_workspace_snapshot_tool.git
cd autoware_workspace_snapshot_tool
./install.sh
```

After installation, you can optionally set up branches and remotes:

```bash
git branch -M <branch name>
git remote add origin <remote repository url>
git push -u origin <branch name>
```

### Uninstall

You can remove the service created by the installation script with the following command:

```bash
systemctl --user stop autoware_workspace_snapshot_tool
systemctl --user disable autoware_workspace_snapshot_tool
rm ~/.config/systemd/user/autoware_workspace_snapshot_tool.service
```
