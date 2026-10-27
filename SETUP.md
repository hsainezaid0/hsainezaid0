# Profile maintenance

This repository powers the profile of **hsainezaid0**. The cards are a static snapshot. Automatic scheduled writes are not enabled.

Edit `profile.json` to change your name, education, interests or toolkit, then regenerate from the saved data:

```bash
python3 generate_profile.py --offline
```

Review and commit the changed SVG files manually to update your profile. The SVG images, generator and snapshot are stored at the repository root.

The current language card counts each public original repository once under its GitHub-reported primary language. It excludes forks and this profile repository. Percentages describe the distribution of repositories, not proficiency or code volume. The source metadata is recorded in `public-snapshot.json`.

The generator also supports a manual live GraphQL read when a GitHub token is supplied through the `GITHUB_TOKEN` environment variable. A live read switches the language measurement to public language bytes. The generator only writes local files; it does not commit, push, schedule jobs or change repository permissions. No personal token is stored in this repository.

Arcade and chess visuals are decorative animations, not playable games.
