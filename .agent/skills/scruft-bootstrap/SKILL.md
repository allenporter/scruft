---
name: scruft-bootstrap
description: Guides the agent in bootstrapping a new project from a Cookiecutter template using scruft, setting up a Python 3.14+ environment with uv, inspecting variables, avoiding directory nesting, and executing post-bootstrap checks.
---

# Bootstrapping Projects with Scruft

This skill provides step-by-step instructions for autonomous agents to bootstrap a new software project using a Cookiecutter template and `scruft`. It ensures a clean, working environment with proper python dependencies and project-level health checks.

## 1. Pre-requisites & Template Selection

### Initial Setup Check
- Ensure that you are executing this inside the target directory (which should be an empty Git repository cloned locally, e.g., containing only a `.git/` folder, a `.gitignore`, or a basic `README.md`).
- Identify the current directory name, which will serve as the project slug (e.g. `my-project`).

### Identify the Template URL
- Locate the template Git URL. If the user did not specify the template URL in their prompt, **ask the user directly** to provide the Cookiecutter/Scruft template URL (e.g., `https://github.com/username/cookiecutter-template`).

---

## 2. Python Environment Setup

Before running `scruft`, set up a virtual environment and install the required tools using `uv`:

1. **Create the virtual environment** (ensuring Python 3.14 or newer is used):
   ```bash
   uv venv --python=3.14
   ```
2. **Activate the environment**:
   ```bash
   source .venv/bin/activate
   ```
3. **Install scruft**:
   ```bash
   uv pip install scruft
   ```

---

## 3. Template Variable Discovery & User Review

Cookiecutter templates define variables (e.g. author name, project description) in a `cookiecutter.json` file. To ensure the project is correctly customized:

1. **Inspect the template configuration**:
   - Locate or temporarily clone the template repository to view its `cookiecutter.json`.
   - Identify all configurable variables and their default values.

2. **Infer smart defaults**:
   - Set project name/slug variables to match the current workspace directory name.
   - Fetch the author's name and email from local Git configurations:
     ```bash
     git config user.name
     git config user.email
     ```

3. **Present Variables for User Approval**:
   - Compile a markdown list or table displaying each cookiecutter key, its default/inferred value, and a brief description.
   - **Stop and ask the user** to confirm these values or provide overrides before proceeding.

---

## 4. Executing Bootstrapping (Avoiding Nested Folders)

To prevent the template from creating a nested folder structure (like `my-project/my-project/...`), we generate files into the parent directory and overwrite existing files in the current folder:

1. **Format the command**:
   - Pass the user-approved extra context as a JSON string using the `--extra-context` flag.
   - Set the output directory to `..` (the parent directory).
   - Use `--overwrite-if-exists` to populate the current cloned repository folder.
   - Use `--no-input` to run non-interactively.

   ```bash
   scruft create <TEMPLATE_URL> --output-dir .. --overwrite-if-exists --no-input --extra-context '{"project_name": "my-project", "project_slug": "my_project", "author_name": "John Doe"}'
   ```

2. **Verify generation**:
   - Confirm that the files were generated directly in your workspace root.
   - Verify that the `.cruft.json` file is present in the workspace root.

---

## 5. Post-Bootstrap Verification & Health Check

After generating files, perform the following validation steps to ensure the project is in a healthy, deployable state:

1. **Initial Commit**:
   - Stage and commit the generated boilerplate so that future template updates can be tracked cleanly via Git:
     ```bash
     git add .
     git commit -m "chore: bootstrap project from template using scruft"
     ```

2. **Workspace Skill & Rule Discovery**:
   - Check if the newly generated project directory contains a `.agent/` or `.agents/` folder.
   - If workspace-specific agent instructions or skills are present, read them (e.g., viewing `SKILL.md` or `AGENTS.md` files) to understand project guidelines and development tasks.

3. **Run Linting & Formatting**:
   - Run the project's default linter/formatter (e.g. `ruff check`, `black`, or `eslint` as defined by the template).
   - If there are any out-of-the-box styling or lint errors, resolve them immediately.

4. **Run Unit Tests**:
   - Locate the test suite (e.g. `pytest` or `npm test`).
   - Run the test command to verify that the template codebase compiles and passes its initial checks. Fix any failing template tests.

5. **CI Config Check**:
   - Inspect `.github/workflows/` or other CI definition folders.
   - Confirm that the CI configuration aligns with the project settings, and inform the user of any secrets or environmental settings that need to be manually configured on GitHub.
