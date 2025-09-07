# ---------- Libraries (standard only) ----------
import os            # filesystem operations (create folders, check paths)
import json          # read/write JSON files
import datetime      # date utilities (used later for default date, validation, etc.)

# ---------- Constants ----------
USERS_FILE   = "storage/users.json"     # global file storing all registered users
DATA_ROOT    = "data"                   # root folder where each user's data will live
EXPENSES_FN  = "expanses.json"          # filename for a user's expenses
SETTINGS_FN  = "settings.json"          # filename for a user's settings
DEFAULT_SETTINGS = {                    # default settings applied if settings.json doesn't exist
  "currency": "USD",
  "categories": ["Food","Transport","Bills","Entertainment","Health","Other"]
}

# ---------- Utility: filesystem & JSON ----------
def ensure_user_dir_exists(username: str) -> None:
    """Make sure a user's folder and JSON files exist with correct structure."""
    # Build the absolute path to the user's folder inside the data root.
    user_dir = os.path.join(DATA_ROOT, username)

    # Create the folder if it does not already exist (idempotent).
    os.makedirs(user_dir, exist_ok=True)

    # Build the full paths for the JSON files inside the user's folder.
    expenses_file = os.path.join(user_dir, EXPENSES_FN)
    settings_file = os.path.join(user_dir, SETTINGS_FN)

    # If expanses.json does not exist, initialize with a dict containing an empty list.
    # This makes it extensible later (e.g., you can add metadata keys without breaking structure).
    if not os.path.exists(expenses_file):
        with open(expenses_file, "w", encoding="utf-8") as f:
            json.dump({"expenses": []}, f, ensure_ascii=False, indent=2)

    # If settings.json does not exist, initialize with DEFAULT_SETTINGS for consistency.
    if not os.path.exists(settings_file):
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, ensure_ascii=False, indent=2)

def ensure_users_file() -> None:
    """Ensure the users file and its parent folder exist with the correct initial shape."""
    # Make sure the parent folder (e.g., "storage/") exists.
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    # Create the file with an empty users list if it doesn't exist.
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": []}, f, ensure_ascii=False, indent=2)

def load_users() -> dict:
    """Load and return the users object from USERS_FILE."""
    # Ensure the file exists before reading.
    ensure_users_file()
    # Read JSON and RETURN it (important).
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users: dict) -> None:
    """Persist the given users dict to USERS_FILE (overwrite)."""
    # Ensure the parent folder exists (safe guard).
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    # Overwrite the file rather than appending (append would corrupt JSON).
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def username_exists(users: dict, username: str) -> bool:
    """Check if a username already exists in the loaded users dict."""
    # Iterate over the list under "users" and return True on first match.
    for u in users.get("users", []):
        if u.get("username") == username:
            return True
    # If no match found, return False.
    return False

def register_user(username: str, password: str) -> None:
    """Register a new user if the username is available, then scaffold their data folder."""
    # Load the current users object.
    users = load_users()
    # Only proceed if the username is not already taken.
    if not username_exists(users, username):
        # Append the new user with plaintext password (v1 scope).
        users["users"].append({"username": username, "password": password})
        # Save updated users file.
        save_users(users)
        # Ensure this user's data directory and baseline JSON files exist.
        ensure_user_dir_exists(username)
    else:
        # If the username is already present, raise a clear error.
        raise ValueError("username already exists")

def authenticate_user(username: str, password: str) -> bool:
    """Return True if a user with matching username and password exists; otherwise False."""
    # Load users from disk.
    users = load_users()
    # Find a record with same username and password.
    for u in users.get("users", []):
        if u.get("username") == username and u.get("password") == password:
            return True
    # No match found -> invalid credentials.
    return False


# --------------- App state & navigation (AUTH -> HOME) ---------------

# Global variables (Python syntax)
state = "AUTH"          # Can be "AUTH" (login/register screen) or "HOME" (after login)
current_user = None     # Will hold {"username": "<name>"} or None

def go_auth() -> None:
    """Switch app to AUTH state and clear current user."""
    global state, current_user           # declare globals to modify them inside the function
    state = "AUTH"
    current_user = None
    # returning is optional; keeping side-effects is enough
    # return state, current_user

def go_home(username: str) -> None:
    """Switch app to HOME state and set the current user."""
    global state, current_user
    state = "HOME"
    current_user = {"username": username}
    # return state, current_user

def action_register(username: str, password: str) -> dict:
    """Try to register, then move to HOME if successful. Return a simple result dict."""
    try:
        # Attempt to create the user; may raise ValueError if username exists
        register_user(username, password)
        # On success, enter HOME with this user
        go_home(username)
        return {"ok": True, "message": "registered and logged in"}
    except ValueError as e:
        # Registration failed (e.g., username already exists)
        return {"ok": False, "message": str(e)}

def action_login(username: str, password: str) -> dict:
    """Try to authenticate; go HOME on success, return error on failure."""
    if authenticate_user(username, password):
        go_home(username)
        return {"ok": True, "message": "logged in"}
    else:
        return {"ok": False, "message": "invalid credentials"}

def action_logout() -> None:
    """Log out and return to AUTH state."""
    go_auth()


# --------------- Expenses I/O & operations ---------------

# ---------- Paths ----------
def expenses_path(username: str) -> str:
    """Return the full path to the expenses.json file for this user."""
    return os.path.join("data", username, "expanses.json")


# ---------- Load / Save ----------
def load_expenses(username: str) -> list[dict]:
    """Load all expenses for a given user as a list of dicts."""
    path = expenses_path(username)

    # If the file does not exist, create it with empty structure.
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"expenses": []}, f, ensure_ascii=False, indent=2)
        return []

    # Read the JSON file.
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Defensive: ensure the key exists and is a list.
    return data.get("expenses", [])


def save_expenses(username: str, items: list[dict]) -> None:
    """Save a list of expense dicts back into the user's expenses.json."""
    path = expenses_path(username)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"expenses": items}, f, ensure_ascii=False, indent=2)


# ---------- Validation helpers ----------
def validate_date_iso(date_str: str) -> None:
    """Raise ValueError if the string is not a valid YYYY-MM-DD date."""
    try:
        datetime.date.fromisoformat(date_str)  # built-in check
    except Exception:
        raise ValueError("date must be in format YYYY-MM-DD")


def validate_amount_positive(x: any) -> float:
    """Convert input to float, ensure it's > 0, return it back."""
    try:
        val = float(x)
    except Exception:
        raise ValueError("amount must be a number")

    if val <= 0:
        raise ValueError("amount must be positive")
    return val


def validate_required_text(s: str, field: str) -> None:
    """Ensure a required text field is non-empty and not just whitespace."""
    if not s or str(s).strip() == "":
        raise ValueError(f"{field} is required")


# ---------- Utility helpers ----------
def today_iso() -> str:
    """Return today's date as an ISO string YYYY-MM-DD."""
    return datetime.date.today().isoformat()


def generate_expense_id() -> str:
    """Generate a unique expense ID based on current timestamp."""
    now = datetime.datetime.now()
    # Example: exp_20250907_153045123
    return "exp_" + now.strftime("%Y%m%d_%H%M%S%f")


def normalize_tags(raw: any) -> list[str]:
    """Normalize the tags field to always be a list of strings."""
    if isinstance(raw, list):
        # Already a list; ensure elements are strings
        return [str(tag).strip() for tag in raw if str(tag).strip()]
    elif isinstance(raw, str):
        # Split by commas if a single string was given
        return [t.strip() for t in raw.split(",") if t.strip()]
    else:
        # If nothing or unexpected type, return empty list
        return []


# ---------- Core operations ----------
def add_expense(username: str, payload: dict) -> str:
    """
    Add a new expense for a user.
    payload should contain:
      - date (YYYY-MM-DD) [optional, default today]
      - amount (number > 0)
      - category (string, required)
      - description (string, optional)
      - payment_method (string, optional)
      - tags (list or comma-separated str, optional)
    """
    # Date: default to today if not provided
    date_str = payload.get("date") or today_iso()
    validate_date_iso(date_str)

    # Amount: must be convertible to positive float
    amount_val = validate_amount_positive(payload.get("amount"))

    # Category: required non-empty text
    validate_required_text(payload.get("category"), "category")

    # Optional fields: description, payment method, tags
    desc = payload.get("description", "")
    method = payload.get("payment_method", "")
    tags = normalize_tags(payload.get("tags"))

    # Load existing expenses
    items = load_expenses(username)

    # Generate unique ID
    eid = generate_expense_id()

    # Build the new expense dict
    new_expense = {
        "id": eid,
        "date": date_str,
        "amount": amount_val,
        "category": payload["category"],
        "description": desc,
        "payment_method": method,
        "tags": tags
    }

    # Append and save
    items.append(new_expense)
    save_expenses(username, items)

    return eid


def list_expenses(username: str, filters: dict | None = None) -> list[dict]:
    """
    Return all expenses for a user, optionally filtered and sorted.
    filters may include:
      - from_date (YYYY-MM-DD)
      - to_date (YYYY-MM-DD)
      - category (exact match)
    """
    items = load_expenses(username)

    # Apply filters if provided
    if filters:
        if "from_date" in filters:
            items = [e for e in items if e["date"] >= filters["from_date"]]
        if "to_date" in filters:
            items = [e for e in items if e["date"] <= filters["to_date"]]
        if "category" in filters:
            items = [e for e in items if e["category"] == filters["category"]]

    # Sort: newest date first, then ID for tie-break
    items.sort(key=lambda e: (e["date"], e["id"]), reverse=True)

    return items


# --------------- Main orchestration ---------------

def boot() -> None:
    """Prepare base folders/files at program startup."""
    ensure_users_file()                       # ensure storage/users.json exists
    os.makedirs(DATA_ROOT, exist_ok=True)     # ensure data/ root exists

# --- DEMO CLI (Interactive Menu) ---
def demo_cli():
    """
    Simple interactive menu for testing:
    - Register / Login
    - Add an expense
    - List expenses
    - Logout / Exit
    """
    import calendar

    boot()       # Ensure base files and folders exist
    go_auth()    # Start in AUTH state (login/register)

    def ask(prompt, allow_empty=False):
        """Helper to get user input, optionally allowing empty values."""
        while True:
            val = input(prompt).strip()
            if val or allow_empty:
                return val
            print("Input cannot be empty.")

    def print_header():
        """Print the header showing current state and user (if logged in)."""
        print("\n" + "="*56)
        if current_user:
            print(f"  Expense Tracker  |  User: {current_user['username']}  |  State: {state}")
        else:
            print(f"  Expense Tracker  |  State: {state}")
        print("="*56)

    # Main loop
    while True:
        print_header()

        # --- AUTH state: only register or login available ---
        if state == "AUTH":
            print("1) Register")
            print("2) Login")
            print("0) Exit")
            choice = ask("> ")

            if choice == "1":
                u = ask("Username: ")
                p = ask("Password: ")
                res = action_register(u, p)
                print(res["message"])

            elif choice == "2":
                u = ask("Username: ")
                p = ask("Password: ")
                res = action_login(u, p)
                print(res["message"])

            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid choice.")

        # --- HOME state: after login ---
        elif state == "HOME":
            print("1) Add expense")
            print("2) List expenses")
            print("3) Logout")
            print("0) Exit")
            choice = ask("> ")

            if choice == "1":
                # Ask for expense details
                date_str = ask("Date (YYYY-MM-DD, empty=today): ", allow_empty=True)
                amount   = ask("Amount: ")
                category = ask("Category: ")
                desc     = ask("Description (optional): ", allow_empty=True)
                method   = ask("Payment method (optional): ", allow_empty=True)
                tags_str = ask("Tags separated by commas (optional): ", allow_empty=True)

                payload = {
                    "date": date_str or None,
                    "amount": amount,
                    "category": category,
                    "description": desc,
                    "payment_method": method,
                    "tags": tags_str
                }
                try:
                    eid = add_expense(current_user["username"], payload)
                    print(f"✅ Added expense with id: {eid}")
                    print(f"Saved in file: {expenses_path(current_user['username'])}")
                except Exception as e:
                    print(f"❌ Error: {e}")

            elif choice == "2":
                # Filtering options
                month = ask("Month filter (YYYY-MM, empty=all): ", allow_empty=True)
                from_date = None
                to_date = None
                if month:
                    y, m = map(int, month.split("-"))
                    last_day = calendar.monthrange(y, m)[1]
                    from_date = f"{month}-01"
                    to_date   = f"{month}-{last_day:02d}"
                else:
                    from_date = ask("From date (YYYY-MM-DD, empty=none): ", allow_empty=True) or None
                    to_date   = ask("To date (YYYY-MM-DD, empty=none): ", allow_empty=True) or None

                category = ask("Category filter (empty=all): ", allow_empty=True) or None
                filters = {}
                if from_date: filters["from_date"] = from_date
                if to_date:   filters["to_date"] = to_date
                if category:  filters["category"] = category

                try:
                    items = list_expenses(current_user["username"], filters or None)
                    if not items:
                        print("(no records)")
                    else:
                        print(f"{'Date':<12} {'Amount':>10}  {'Category':<14} {'Description'}")
                        print("-"*56)
                        for e in items:
                            print(f"{e['date']:<12} {e['amount']:>10.2f}  {e['category']:<14} {e.get('description','')}")
                        print("-"*56)
                        print(f"Total records: {len(items)}")
                except Exception as e:
                    print(f"❌ Error: {e}")

            elif choice == "3":
                action_logout()
                print("Logged out.")

            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid choice.")


# --- Replace your old main() with this ---
def main():
    demo_cli()

if __name__ == "__main__":
    main()
