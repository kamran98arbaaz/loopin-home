import json
from datetime import datetime

# Load existing updates
def load_updates():
    try:
        with open('updates.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Save all updates
def save_updates(updates):
    with open('updates.json', 'w') as file:
        json.dump(updates, file, indent=4)
     

# Add a new update
def add_update():
    name = input("Enter your name: ")
    message = input("What's your update? ")
    
    update = {
        "name": name,
        "message": message,
        "timestamp": datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    
    }
    
    updates = load_updates()
    updates.append(update) 
    save_updates(updates) 
    print("\n✅ Update added successfully!\n")
    
# Show all updates
def view_updates():
    updates = load_updates()
    print("\n📋 Team Updates:\n")
    for update in updates:
        print(f"[{update['timestamp']}] {update['name']} says: {update['message']}")
    print("\n")
    
# Delete an update manually
def delete_update():
    updates = load_updates()

    if not updates:
        print("\n📭 No updates to delete.\n")
        return

    print("\n🗑️ Select an update to delete:\n")
    for idx, update in enumerate(updates, 1):
        print(f"{idx}. [{update['timestamp']}] {update['name']} says: {update['message']}")

    try:
        choice = int(input("\nEnter the number of the update to delete: "))
        if 1 <= choice <= len(updates):
            confirm = input(f"Are you sure you want to delete this update? (y/n): ").lower()
            if confirm == 'y':
                deleted = updates.pop(choice - 1)
                save_updates(updates)
                print(f"\n✅ Deleted update from {deleted['name']}.\n")
            else:
                print("\n❎ Deletion canceled.\n")
        else:
            print("\n❌ Invalid number.\n")
    except ValueError:
        print("\n⚠️ Please enter a valid number.\n")    

# Menu system
def main():
    while True:
        print("=== Hackonauts Team Board ===")
        print("1. Add Update")
        print("2. View Updates")
        print("3. Delete an Update")
        print("4. Exit")
        
        choice = input("Choose an option: ")
        
        if choice == '1':
            add_update()
        elif choice == '2':
            view_updates()
        elif choice == '3':
            delete_update()
        elif choice == '4':
            print("👋 Exiting. See you next time!")
            break
        else:
            print("❌ Invalid choice. Try again.\n")
            
if __name__ == "__main__":
    main()                    

# Show all updates and allow user to mark them as seen
def view_updates():
    current_user = input("Enter your name to view updates: ")
    updates = load_updates()
    updated = False
    
    print("\n📋 Team Updates:\n")
    for update in updates:
        # Initialize seen_by if not already present
        if "seen_by" not in update:
            update["seen_by"] = []
        
        status = "👁️ Seen" if current_user in update["seen_by"] else "🆕 New"
        print(f"[{update['timestamp']}] {update['name']} says: {update['message']} ({status})")
        
        # Mark as seen if not already
        if current_user not in update["seen_by"]:
            update["seen_by"].append(current_user)
            updated = True          
    
    if updated:
        save_updates(updates)
        print("\n✅ Marked all updates as seen.\n")
    else:
        print("\nNo new updates. You're all caught up!\n")
        




       
              