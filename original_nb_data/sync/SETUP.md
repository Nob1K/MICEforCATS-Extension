# Google Drive sync - first-time setup

This involves a slightly tedious setup if you don't ever use gcp, I will try to sync and push to github as much as I can. If too lazy just git pull and hopefully latest stuff is on there.
You only do this once. End result: `credentials.json` and `token.json` in this folder that lets `pull.py` authenticate as you.

---

## 1. Create a Google Cloud project

1. Go to <https://console.cloud.google.com/>
2. Top bar -> project picker -> **New Project**
3. Name it anything and Leave org as-is. **Create**
4. Make sure the new project is selected in the top bar before continuing

## 2. Enable the Google Drive API

1. Left menu → **APIs & Services** -> **Library**
2. Search **Google Drive API** -> **Enable**

## 3. Configure the OAuth consent screen

1. Left menu -> **APIs & Services** -> **OAuth consent screen**
2. User type: **External** -> **Create**
3. Fill in:
   - App name: anything (e.g. `drive-sync`)
   - User support email: your address
   - Developer contact email: your address
   - Leave everything else blank -> **Save and Continue**
4. **Scopes** page -> skip (**Save and Continue**). The script requests its
   scope at runtime.
5. **Test users** page -> **Add Users** -> add your own Google address ->
   **Save and Continue**. *This step is critical.* Without it, the app is in
   "testing" mode and only listed test users can authenticate; everyone else
   gets `Error 403: access_denied`.
6. **Summary** -> **Back to Dashboard**

## 4. Create an OAuth client ID

1. Left menu -> **APIs & Services** -> **Credentials**
2. **Create Credentials** -> **OAuth client ID**
3. Application type: **Desktop app**. Name: anything.
4. **Create** -> a dialog appears -> **Download JSON**.
5. Rename the downloaded file to **`credentials.json`** and move it into this
   folder (`original_files/sync/`).

## 5. First run

From this folder:

```bash
source .venv/bin/activate
python pull.py <FILE_ID> <DEST_PATH>
```

A browser window opens asking you to sign in and grant the app
read-only Drive access. Approve it. The script saves a `token.json` here so
future runs don't prompt.

If the browser doesn't open automatically, the script prints
a URL, paste it into your host browser. The redirect target is
`http://localhost:<random-port>`

### Getting a file ID

Find ID in Colab notebooks' URL pattern:

```
https://colab.research.google.com/drive/1aBcD3FgH...XYZ?...
                                        ^^^^^^^^^^^^^^^
```


---

## Troubleshoot

- **`Error 403: access_denied`** - your account isn't in the Test Users list
  (step 3.5). Add it.
- **`invalid_grant` / token errors** - delete `token.json` and re-run
- **Permission denied on the file itself** - the Drive file isn't shared with
  the Google account you authenticated as. Either share it, or re-auth as
  the owning account (delete `token.json` first)
- **Need to re-auth as a different user** - `rm token.json` and run again
