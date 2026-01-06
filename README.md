# **ArcGIS Enterprise Service Update Script**

This script automates the process of updating a hosted service in ArcGIS Enterprise using a Service Definition (.sd) file. It includes error handling to detect and repair "zombie" services (where the Portal Item exists, but the backend REST endpoint is missing).

## **Requirements**

* Python 3.x  
* ArcGIS API for Python (pip install arcgis)  
* Network access to the ArcGIS Enterprise Portal  
* Administrator credentials or ownership of the target services

## **Configuration**

Open the script and modify the CONFIG dictionary at the bottom of the file with your specific environment details:

* **url**: The full URL to your ArcGIS Enterprise Portal (e.g., https://webadaptor.domain.com/portal).  
* **username**: The username of an account with permission to overwrite the service.  
* **password**: The password for the account.  
* **sd\_item\_id**: The Item ID of the source Service Definition file hosted in the portal.  
* **target\_id**: The Item ID of the hosted Feature Service you wish to update.  
* **temp\_dir**: A local directory path where the script can temporarily download the .sd file.

## **Operational Logic**

The script follows this decision tree:

1. **Check Target Item:** Verifies if the target\_id exists in the Portal.  
2. **Scenario A \- Item Missing:**  
   * If the item is not found, the script attempts to publish the SD file as a new service using the provided target\_id to ensure ID consistency.  
3. **Scenario B \- Item Exists:**  
   * The script attempts to access the service manager.  
   * **If Healthy:** It performs a standard overwrite operation using the downloaded SD file.  
   * **If Broken (404/500 Error):** It identifies the item as a "zombie." It deletes the broken item and immediately republishes the service using the original target\_id.

