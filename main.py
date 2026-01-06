import os
import json
from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection

def get_service_name_from_url(url):
    """
    Extracts the service name from a REST URL.
    Example: .../services/Planning/My_Layer/FeatureServer -> 'My_Layer'
    """
    try:
        # Split by '/' and find the part before 'FeatureServer' or 'MapServer'
        parts = url.split('/')
        if 'FeatureServer' in parts:
            idx = parts.index('FeatureServer')
            return parts[idx - 1]
        elif 'MapServer' in parts:
            idx = parts.index('MapServer')
            return parts[idx - 1]
        return None
    except:
        return None

def service_update(portal_url, username, password, sd_item_id, target_item_id, temp_dir):
    """
    overwrites an item based on a sd
    Alternately, if the layer is borked, delete the feature layer and republish using the sd at the same itemID
    """
    try:
        #Connect
        print(f"Connecting to {portal_url}...")
        gis = GIS(portal_url, username, password)
        print("Logged in.")

        #Get Source SD
        print(f"Retrieving Source SD (ID: {sd_item_id})...")
        sd_item = gis.content.get(sd_item_id)
        if not sd_item: raise ValueError("Source SD not found.")

        #Get Target Item
        print(f"Retrieving Target Item (ID: {target_item_id})...")
        target_item = gis.content.get(target_item_id)
        if not target_item:
            publish_params = {"itemIdToCreate" : target_item_id}
            print("Target item not found. Publishing new service at defined itemid")
            sd_item.publish(publish_parameters=publish_params, item_id = target_item_id)
            return

        #Download SD locally (Needed for both overwrite and republish)
        print(f"Downloading .sd file to {temp_dir}...")
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        local_sd_path = sd_item.download(save_path=temp_dir)
        print(f"Source file ready: {local_sd_path}")

        #Attempt Overwrite with "Zombie" Handling
        #Should only work if service exists but item doesn't 
        #Which isn't our scenario
        try:
            print("Attempting standard overwrite...")
            
            # This line will crash if the backend service is 404
            flc = FeatureLayerCollection.fromitem(target_item)
            
            # If we get here, the service exists, so we overwrite normally
            flc.manager.overwrite(local_sd_path)
            print("SUCCESS: Service overwritten normally.")

        except Exception as e:
            #DELETE & REPUBLISH
            error_msg = str(e)
            
            # Check for 404 (Not Found) or 500 (Internal Server Error)
            #CHecking 500 probably a mistake. Should 404 when zombified
            if "404" in error_msg or "not found" in error_msg.lower() or "500" in error_msg:
                print(f"\ERROR: {error_msg}")
                print(">> DIAGNOSIS: Zombie Item detected. Initiating Delete & Republish workflow.")

                #Delete broken item
                try:
                    
                    print(f"Deleting broken item {target_item_id}...")
                    target_item.delete()
                    print(">> Item deleted.")

                    
                    print(f"Publishing new service at defined itemid ({target_item_id})...")

                    #I dont think I need this but IIAB
                    publish_params = {"itemIdToCreate": target_item_id}
                    #Publish at original itemid
                    sd_item.publish(publish_parameters=publish_params, item_id=target_item_id)
                    
                    print("Service recreated with original ID.")

                except Exception as publish_error:
                    print(f"Could not republish after delete. {publish_error}")
            else:
                # If the error was something else (like permission denied), raise it
                raise e

    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")

# --- Configuration Section ---
CONFIG = {
    "url": "https://webadaptor.name/portal",
    "username": "USERNAME",
    "password": "PASSWORD",
    "sd_item_id": "2d108c778be64ebfb65019ee4b8bfab9",   # ID of the .sd file
    "target_id": "ea7e454e0a5a438dbec9479c75ad43c4",   # ID of the Feature Layer to overwrite
    "temp_dir": r"C:\temp\arcgis_updates"               # Local folder for temporary download
}

if __name__ == "__main__":
    service_update(
        CONFIG["url"],
        CONFIG["username"],
        CONFIG["password"],
        CONFIG["sd_item_id"],
        CONFIG["target_id"],
        CONFIG["temp_dir"]
    )