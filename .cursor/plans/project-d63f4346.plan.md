<!-- d63f4346-59b2-42a1-9c12-00affe1433a3 2e256885-8be9-4a43-bde8-26e40673140f -->
# Git Push Plan

1. **Prep repository**  

- Ensure git is initialized.  
- Write a `.gitignore` excluding large/sensitive folders (`data/`, `output/`, virtualenvs, etc.).  
- Stage all relevant files and commit with a descriptive message.

2. **Push to GitHub**  

- Add the remote `origin` pointing to `git@github.com:vinayakgrover/sonic-sanitize.git`.  
- Push the main branch (`main` or `master`) to GitHub.

3. **Verify & report**  

- Run `git status` to confirm a clean working tree.  
- Provide a short summary of what was pushed and next steps (e.g., tag/release if needed).