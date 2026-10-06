"""One-click launcher: creates .env, builds the MySQL database (first run only) and starts IT Assist."""
import getpass, os, re, sys, threading, webbrowser
import mysql.connector

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)


def read_env():
    env = {"DB_HOST": "localhost", "DB_PORT": "3306", "DB_USER": "root", "DB_PASSWORD": "", "DB_NAME": "it_assist"}
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def write_env(env):
    with open(".env", "w", encoding="utf-8") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")


def connect(env, with_db=False):
    kw = dict(host=env["DB_HOST"], port=int(env["DB_PORT"]), user=env["DB_USER"], password=env["DB_PASSWORD"])
    if with_db:
        kw["database"] = env["DB_NAME"]
    return mysql.connector.connect(**kw)


def run_sql_file(cur, path):
    text = open(path, encoding="utf-8").read()
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))
    for stmt in text.split(";"):
        if stmt.strip():
            cur.execute(stmt)


def main():
    env = read_env()
    conn = None
    while conn is None:
        try:
            conn = connect(env)
        except mysql.connector.Error as e:
            print(f"\nCould not connect to MySQL as '{env['DB_USER']}' on {env['DB_HOST']}: {e.msg}")
            if e.errno == 2003:
                print("MySQL does not seem to be running. Start the MySQL service and try again.")
                input("Press Enter to exit...")
                return
            env["DB_PASSWORD"] = getpass.getpass("Enter your MySQL root password: ")
    write_env(env)

    cur = conn.cursor()
    cur.execute("SHOW DATABASES LIKE %s", (env["DB_NAME"],))
    has_data = False
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name='assets'", (env["DB_NAME"],))
        if cur.fetchone()[0]:
            cur.execute(f"SELECT COUNT(*) FROM `{env['DB_NAME']}`.assets")
            has_data = cur.fetchone()[0] > 0
    if has_data:
        print("Database already set up - keeping your existing data.")
    else:
        print("Creating database and loading sample data...")
        run_sql_file(cur, "database/schema.sql")
        run_sql_file(cur, "database/seed.sql")
        conn.commit()
        print("Database ready.")
    conn.close()

    from app import app
    url = "http://127.0.0.1:5000"
    print(f"\nIT Assist is running at {url}\nLogin: admin / admin123\nPress Ctrl+C to stop.\n")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
