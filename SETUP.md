# Profile maintenance

This repository powers the profile of **hsainezaid0**.

Edit `profile.json` to change your name, education, interests or toolkit, then run **Actions → Refresh profile cards → Run workflow**. The cards refresh daily through GitHub Actions using the repository-provided temporary token. No personal access token or paid image service is required.

The SVG images, generator and public data snapshot are stored at the repository root. Arcade and chess visuals are decorative animations. Language percentages measure public repository language bytes, excluding forks and this profile repository; they do not measure proficiency.

To regenerate from the saved snapshot locally:

```bash
python3 generate_profile.py --offline
```

A failed API sync preserves the previous cards. The workflow only stages generated SVG files and the snapshot. Daily jobs can be delayed by GitHub and scheduled jobs may be paused after prolonged repository inactivity; run the workflow manually to resume.
