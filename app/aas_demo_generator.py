import aas_core3
import aas_core3.types
import aas_core3.xmlization as aas_xmlization

import shutil
import os
import zipfile
from tempfile import TemporaryDirectory


global work_dir
work_dir = None


# type = "internal" || "external"
def create_demo_aasx(product_id: str, serial_number: str, type: str, total_pcf = 0.0):
    global work_dir
    work_dir = TemporaryDirectory()

    # unpack template aasx file
    resource_name = f"{product_id}_{type}.aasx"
    aasx_path = f"{work_dir.name}/{resource_name}"
    shutil.copy(f"data/InstanceDemo/{resource_name}", aasx_path)

    zip_path = f"{work_dir.name}/{product_id}_{type}.zip"
    shutil.move(aasx_path, zip_path)

    unzip_dir = f"{work_dir.name}/{product_id}_{type}"
    os.makedirs(unzip_dir)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(unzip_dir)

    path_map = {
        "58841+internal": "aasx/AssetAdministrationShell---2DB29DAD/AssetAdministrationShell---2DB29DAD.aas.xml",
        "58841+external": "aasx/AssetAdministrationShell---2DB29DAD/AssetAdministrationShell---2DB29DAD.aas.xml",
        "54530+internal": "aasx/Murrelektronik_VX00_BPC05_0100001/Murrelektronik_VX00_BPC05_0100001.aas.xml",
        "54530+external": "aasx/Murrelektronik_VX00_BPC05_0100001/Murrelektronik_VX00_BPC05_0100001.aas.xml"
    }

    template_xml_path = f"{work_dir.name}/{product_id}_{type}/{path_map[f"{product_id}+{type}"]}"

    # edit template
    env = aas_xmlization.environment_from_file(template_xml_path)

    replace_serial_number(env, product_id, serial_number, type, total_pcf)

    # repack
    with open(template_xml_path, "w", encoding="utf-8") as f:
        f.write(aas_xmlization.to_str(env))
    
    shutil.make_archive(unzip_dir, format="zip", root_dir=unzip_dir)
    shutil.move(zip_path, aasx_path)

    #work_dir.cleanup()
    print('ASS created:', aasx_path)
    return aasx_path


# Replaces serial number at:
# 1. aas id_short
# 2. aas id
# 3. aas global asset id
# 4. aas submodel refs
# 5. submodel ids
# 6. nameplate.serial_number  
def replace_serial_number(env: aas_core3.types.Environment, product_id: str, serial_number: str, type: str, total_pcf):
    aas = env.asset_administration_shells[0]
    
    # 1.
    aas.id_short = f"Murrelektronik_{product_id}_{serial_number}"

    # 2.
    if type == "internal":
        # aas.id = f"http://deopp-aasinst-01/{product_id}/aas/0/0/{serial_number}"
        # aas.id = f"http://deopp-aasinst-01/{product_id}/aas/1/0/{serial_number}"
        aas.id = f"https://aas.intern.murrleketronik.com/{product_id}/aas/1/0/{serial_number}"  # <---- changed
    else:
        aas.id = f"https://aas.murrelektronik.com/{product_id}/aas/1/0/{serial_number}"

    # 3.
    # if type == "internal":
    #     aas.asset_information.global_asset_id = f"http://deopp-aasinst-01/{product_id}/{serial_number}"
    # else:
    #     aas.asset_information.global_asset_id = f"https://aas.murrelektronik.com/{product_id}/{serial_number}"
    aas.asset_information.global_asset_id = f"https://aas.murrelektronik.com/{product_id}/{serial_number}"       #

    # 5.

    submodels = env.submodels
    
    new_submodel_ids = {}
    for submodel in submodels:
        old_submodel_id = submodel.id

        parts = old_submodel_id.split('/')
        parts[-2] = serial_number
        
        new_submodel_id = '/'.join(parts)

        # store for later
        new_submodel_ids[old_submodel_id] = new_submodel_id

        submodel.id = new_submodel_id

        #6. 
        if submodel.id_short == "Nameplate":
            for submodel_element in submodel.submodel_elements:
                if submodel_element.id_short == "SerialNumber":
                    submodel_element.value = serial_number
        
        if submodel.id_short == "CarbonFootprint":
            submodel.submodel_elements[0].value[1].value[1].value = str(total_pcf)
    
    # 4.
    for submodel_ref in aas.submodels:
        old_ref = submodel_ref.keys[0].value

        new_ref = new_submodel_ids[old_ref]

        submodel_ref.keys[0].value = new_ref


def clean_up():
    global work_dir
    work_dir.cleanup()


if __name__ == "__main__":
   print(create_demo_aasx("54530", "aaaaaaaaaaaaa", "external", 2.0))
