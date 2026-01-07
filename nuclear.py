import os
from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection

# --- Configuration Section ---
CONFIG = {
    "url": "https://webadaptor.name/portal",
    "username": "ADMINUSER",
    "password": "ADMINPASSWORD",
    "temp_dir": r"C:\temp\arcgis_updates",
    # query to find all SDs. You can add 'owner:xyz' to test on a specific user first.
    "search_query": 'type:"Service Definition"' 
}

def find_associated_layer(gis, sd_item):
    """
    Attempts to find the Feature Layer associated with a Service Definition.
    1. Checks explicit 'Service2Data' relationship.
    2. Falls back to searching for a Feature Layer with the exact same title and owner.
    """
    # Strategy 1: Check Relationships
    try:
        related_items = sd_item.related_items(rel_type='Service2Data', direction='forward')
        for item in related_items:
            if item.type == "Feature Service" or item.type == "Feature Layer":
                return item
    except Exception:
        pass

    # Strategy 2: Fallback search by Title and Owner
    # This is risky if multiple items share a title, but necessary if relationships are broken
    search_res = gis.content.search(
        query=f'title:"{sd_item.title}" AND owner:"{sd_item.owner}" AND type:"Feature Service"',
        max_items=1
    )
    if search_res:
        return search_res[0]
    
    return None

def service_update(gis, sd_item, target_item, temp_dir):
    """
    Performs the Overwrite -> Fail -> Delete -> Republish -> Reassign Owner workflow.
    """
    # Capture IDs and Owner for logic
    sd_item_id = sd_item.id
    target_item_id = target_item.id
    original_owner = target_item.owner
    
    print(f"Processing: {target_item.title}")
    print(f"Target Owner: {original_owner} | SD ID: {sd_item_id} | Target ID: {target_item_id}")

    try:
        # Download SD locally (Needed for both overwrite and republish)
        if not os.path.exists(temp_dir): 
            os.makedirs(temp_dir)
            
        # Clean filename to avoid issues
        clean_title = "".join(x for x in sd_item.title if x.isalnum() or x in "._- ")
        save_name = f"{clean_title}.sd"
        
        print(f"Downloading .sd file...")
        local_sd_path = sd_item.download(save_path=temp_dir, file_name=save_name)

        # Attempt Standard Overwrite
        try:
            print("Attempting standard overwrite...")
            
            # This triggers the 404/500 if the backend is a "zombie"
            flc = FeatureLayerCollection.fromitem(target_item)
            flc.manager.overwrite(local_sd_path)
            print("Service overwritten normally.")

        except Exception as e:
            error_msg = str(e)
            
            # Check for generic connection errors vs actual service failures
            # Expanded checks for 500, 404, or "does not exist"
            is_zombie_error = any(x in error_msg.lower() for x in ["404", "not found", "500", "internal server error"])

            if is_zombie_error:
                print(f"ERROR: {error_msg}")
                print("Initiating Delete & Republish workflow.")

                try:
                    # 1. Delete broken item
                    print(f"Deleting broken item {target_item_id}...")
                    target_item.delete()
                    print("deleted.")

                    # 2. Publish new service at defined itemid
                    print(f"Publishing new service at defined itemid ({target_item_id})...")
                    publish_params = {
                        "itemIdToCreate": target_item_id,
                        "overwrite": True
                    }
                    
                    # Publish creates the item under the CURRENT ADMIN USER
                    new_item = sd_item.publish(
                        publish_parameters=publish_params, 
                        item_id=target_item_id,
                        file_type='serviceDefinition'
                    )
                    
                    if new_item:
                        print(">> Service recreated with original ID.")
                        
                        # 3. Reassign Ownership
                        # If the admin running this is not the original owner, give it back
                        if new_item.owner != original_owner:
                            print(f"Reassigning ownership to original owner: {original_owner}")
                            new_item.reassign_to(original_owner)
                            print("Reassigned")
                    else:
                        print("!! WARNING: Publish returned None, but no error raised. Check Portal.")

                except Exception as publish_error:
                    print(f"CRITICAL: Could not republish after delete. {publish_error}")
            else:
                # If error is unrelated to service state (e.g. file lock, permissions), raise it
                print(f"Standard Overwrite failed with non-zombie error: {e}")
                
    except Exception as e:
        print(f"CRITICAL FAILURE processing {target_item.title}: {e}")

def main():
    # Connect
    print(f"Connecting to {CONFIG['url']}...")
    gis = GIS(CONFIG["url"], CONFIG["username"], CONFIG["password"])
    print("Logged in.")

    # 1. Search for all Hosted Service Definitions
    print(f"Searching for items matching: {CONFIG['search_query']}...")
    sd_items = gis.content.search(query=CONFIG['search_query'], max_items=-1)
    
    print(f"Found {len(sd_items)} Service Definitions. Beginning iteration...")

    for sd in sd_items:
        # 2. Find the matching Feature Layer (The Target)
        target_layer = find_associated_layer(gis, sd)

        if target_layer:
            # 3. Run the update logic
            service_update(gis, sd, target_layer, CONFIG["temp_dir"])
        else:
            print(f"SKIPPING: Could not find a Feature Layer associated with SD '{sd.title}' ({sd.id})")

if __name__ == "__main__":
    main()