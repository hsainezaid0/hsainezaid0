# Profile maintenance

This repository powers the profile of **hsainezaid0**. The cards are a static snapshot. Automatic scheduled writes are not enabled.

Edit `profile.json` to change your name, education, interests, toolkit or featured project labels and tags, then regenerate from the saved data:

```bash
python3 generate_profile.py --offline
```

Review and commit the changed SVG files and generated `README.md` manually to update your profile. The SVG images, generator and snapshot are stored at the repository root. Every visible section of the README uses the same terminal palette, including the biography, project gallery, contribution heatmap, city, language stack, arcade, links and footer. GitHub controls the sidebar, native pinned cards and native contribution calendar outside the README.

The current language card counts each public original repository once under its GitHub-reported primary language. It excludes forks and this profile repository. Percentages describe the distribution of repositories, not proficiency or code volume. The source metadata is recorded in `public-snapshot.json`.

The circular rings on individual project cards show that repository's primary language percentage, as displayed by GitHub's language breakdown. They do not indicate project completion or proficiency. Project descriptions, stars and code push dates come from the public repository metadata. Each gallery card links to its real repository. Project selection and display labels are configured in `featured_projects` in `profile.json`.

The heatmap and three-dimensional city use the same daily contribution counts. The snapshot date is displayed in the visuals. The heatmap includes GitHub's partial boundary weeks and uses color intensity relative to the busiest day in the saved calendar.

The generator also supports a manual live GraphQL read when a GitHub token is supplied through the `GITHUB_TOKEN` environment variable. A live read switches the language measurement to public language bytes. The generator only writes local files; it does not commit, push, schedule jobs or change repository permissions. No personal token is stored in this repository.

Arcade and chess visuals are decorative animations, not playable games.
