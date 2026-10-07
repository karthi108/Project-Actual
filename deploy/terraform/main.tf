resource "openstack_networking_secgroup_v2" "private_rehearsal" {
  count                = var.enable_rehearsal ? 1 : 0
  name                 = "actual-synthetic-rehearsal"
  description          = "Operator SSH only; application and database stay on loopback"
  delete_default_rules = true
}

resource "openstack_networking_secgroup_rule_v2" "operator_ssh" {
  count             = var.enable_rehearsal ? 1 : 0
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = var.operator_cidr
  security_group_id = openstack_networking_secgroup_v2.private_rehearsal[0].id
}

# Egress is absent by default. An operator must design reviewed update/registry egress
# before rehearsal; this config never guesses an unrestricted outbound policy.
resource "openstack_compute_instance_v2" "rehearsal" {
  count           = var.enable_rehearsal ? 1 : 0
  name            = "actual-synthetic-rehearsal"
  image_id        = var.image_id
  flavor_id       = var.flavor_id
  key_pair        = var.existing_key_pair
  security_groups = [openstack_networking_secgroup_v2.private_rehearsal[0].name]
  user_data       = file("${path.module}/cloud-init.yaml")
  network {
    uuid = var.network_id
  }
  lifecycle {
    prevent_destroy = true
  }
}
