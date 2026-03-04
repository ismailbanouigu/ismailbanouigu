- 👋 Hi, I’m @ismailbanouigu
- 👀 I’m interested in ...
- 🌱 I’m currently learning ...
- 💞️ I’m looking to collaborate on ...
- 📫 How to reach me ...

## Outlook automation prototype

I added a first working prototype script: `outlook_automation.py`.

### What it does

1. Takes your **first name**, **last name**, and **country**.
2. Tries `<firstname><lastname>@outlook.com` first.
3. Checks if that Outlook address appears to already exist using Microsoft credential lookup.
4. If taken, it fetches fallback name candidates from Fantasy Name Generators using the country slug.
5. Keeps checking candidates until it finds an available one.
6. Generates a strong password between **8 and 12 characters**.

### Run

```bash
python3 outlook_automation.py "John" "Doe" "Japan"
```

### Notes

- This script helps with **name availability + password generation only**.
- If your network blocks Microsoft endpoints, you can run with `--skip-availability-check` to test the flow offline.
- It does **not** create the Outlook account (that step can hit anti-bot checks / CAPTCHA).
- Country pages on Fantasy Name Generators vary; if no names are returned, try another country keyword.

<!---
ismailbanouigu/ismailbanouigu is a ✨ special ✨ repository because its `README.md` (this file) appears on your GitHub profile.
You can click the Preview link to take a look at your changes.
--->
