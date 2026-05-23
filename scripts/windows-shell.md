# Windows Shell Notes

## Root Cause From npm Log
The npm debug log showed:

```text
cwd C:\Users\Anton L
error path C:\Users\Anton L\package.json
```

That means `npm run dev -- --port 3000` was launched from the user home directory, not from `C:\Users\Anton L\snipe-leads`. npm resolves scripts from the current working directory unless `--prefix` is supplied.

## Stable Commands
From anywhere:

```powershell
npm.cmd --prefix "C:\Users\Anton L\snipe-leads" run dev -- --port 3000
npm.cmd --prefix "C:\Users\Anton L\snipe-leads" run type-check
npm.cmd --prefix "C:\Users\Anton L\snipe-leads" run build
```

From the project root:

```powershell
.\snipra.cmd dev --port 3000
.\snipra.cmd type-check
.\snipra.cmd build
```

Use `npm.cmd` on Windows PowerShell when execution policy blocks `npm.ps1`.
