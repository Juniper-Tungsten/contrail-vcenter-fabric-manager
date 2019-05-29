import mock
import pytest
from vnc_api import vnc_api

from cvfm import models
from cvfm.services import VirtualMachineInterfaceService


@pytest.fixture
def vmi_service(vnc_api_client):
    return VirtualMachineInterfaceService(None, vnc_api_client, None)


def test_create_vmi_model(vmi_service, vm_model):
    vmi_models = vmi_service.create_vmi_models_for_vm(vm_model)

    assert vmi_models[0].uuid == models.generate_uuid("esxi-1_dvs-1_dpg-1")
    assert vmi_models[0].host_name == "esxi-1"
    assert vmi_models[0].dpg_model.name == "dpg-1"
    assert (
        vmi_models[0].dpg_model.uuid == "5a6bd262-1f96-3546-a762-6fa5260e9014"
    )
    assert vmi_models[0].dpg_model.dvs_name == "dvs-1"
    assert vmi_models[0].dpg_model.vlan_id == 5
    assert vmi_models[0].vpg_uuid == models.generate_uuid("esxi-1_dvs-1")


def test_create_vmi_in_vnc(vmi_service, vnc_api_client, project, fabric_vn):
    vnc_api_client.read_vn.return_value = fabric_vn
    vnc_api_client.read_vmi.return_value = None

    dpg_model = models.DistributedPortGroupModel(
        uuid="5a6bd262-1f96-3546-a762-6fa5260e9014",
        key="dvportgroup-1",
        name="dpg-1",
        vlan_id=5,
        dvs_name="dvs-1",
    )
    vmi_model = models.VirtualMachineInterfaceModel(
        uuid="0b1016bf-374b-3829-afba-807b8bf8396a",
        host_name="esxi-1",
        dpg_model=dpg_model,
    )

    vmi_service.create_vmi_in_vnc(vmi_model)

    created_vmi = vnc_api_client.create_vmi.call_args[0][0]
    assert created_vmi.name == "esxi-1_dvs-1_dpg-1"
    assert created_vmi.uuid == "0b1016bf-374b-3829-afba-807b8bf8396a"
    assert created_vmi.parent_name == project.name
    assert len(created_vmi.virtual_network_refs) == 1
    assert (
        created_vmi.virtual_network_refs[0]["uuid"]
        == "5a6bd262-1f96-3546-a762-6fa5260e9014"
    )
    assert (
        created_vmi.virtual_machine_interface_properties.sub_interface_vlan_tag
        == 5
    )


def test_attach_vmi_to_vpg(vmi_service, vnc_api_client):
    vnc_vpg = vnc_api.VirtualPortGroup()
    vnc_api_client.read_vpg.return_value = vnc_vpg

    dpg_model = models.DistributedPortGroupModel(
        uuid="5a6bd262-1f96-3546-a762-6fa5260e9014",
        key="dvportgroup-1",
        name="dpg-1",
        vlan_id=5,
        dvs_name="dvs-1",
    )
    vmi_model = models.VirtualMachineInterfaceModel(
        uuid="0b1016bf-374b-3829-afba-807b8bf8396a",
        host_name="esxi-1",
        dpg_model=dpg_model,
    )

    vmi_service.attach_vmi_to_vpg(vmi_model)

    assert len(vnc_vpg.virtual_machine_interface_refs) == 1


def test_find_affected_vmis(vmi_service, vmware_vm):
    dpg_model = models.DistributedPortGroupModel(
        uuid=models.generate_uuid("dvs-1_dpg-2"),
        key="dvportgroup-2",
        name="dpg-2",
        vlan_id=6,
        dvs_name="dvs-1",
    )
    old_vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm)
    new_vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm)

    vmis_to_delete_1, vmis_to_create_1 = vmi_service.find_affected_vmis(
        old_vm_model, new_vm_model
    )

    assert len(vmis_to_delete_1) == 0
    assert len(vmis_to_create_1) == 0

    new_vm_model.dpg_models = [dpg_model]
    vmis_to_delete_2, vmis_to_create_2 = vmi_service.find_affected_vmis(
        old_vm_model, new_vm_model
    )

    assert len(vmis_to_delete_2) == 1
    assert len(vmis_to_create_2) == 1
    assert list(vmis_to_delete_2)[0].uuid == models.generate_uuid(
        'esxi-1_dvs-1_dpg-1'
    )
    assert list(vmis_to_create_2)[0].uuid == models.generate_uuid(
        'esxi-1_dvs-1_dpg-2'
    )
