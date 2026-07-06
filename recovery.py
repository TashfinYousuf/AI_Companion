import sqlite3

def nuclear_recovery():
    OLD_ID = "tashfin_01"
    NEW_UID = "GtRgmHp0ItMB8cWOv85ApTB3FBI3" 
    
    databases = ["aura.db", "local.db"]
    
    for db_path in databases:
        print(f"\n☢️ Scanning database: {db_path}...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            updated_something = False
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                for col in columns:
                    col_name = col[1]
                    try:
                        # ডাটাবেসের যেকোনো জায়গায় (এমনকি JSON-এর ভেতরেও) যদি tashfin_01 থাকে, সেটাকে রিপ্লেস করবে
                        query = f"UPDATE {table_name} SET {col_name} = REPLACE(CAST({col_name} AS TEXT), ?, ?) WHERE CAST({col_name} AS TEXT) LIKE ?"
                        cursor.execute(query, (OLD_ID, NEW_UID, f'%{OLD_ID}%'))
                        
                        if cursor.rowcount > 0:
                            print(f"✅ HACKED & REPLACED {cursor.rowcount} items in -> Table: '{table_name}', Column: '{col_name}'")
                            updated_something = True
                    except:
                        pass # যদি কোনো বাইনারি কলাম থাকে, সেটা ইগনোর করবে
                        
            if updated_something:
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Error in {db_path}: {e}")

    print("\n🎉 NUCLEAR RECOVERY COMPLETE! Now absolutely NOTHING is tied to 'tashfin_01'.")

if __name__ == "__main__":
    nuclear_recovery()