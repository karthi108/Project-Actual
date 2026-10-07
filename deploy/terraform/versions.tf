terraform {
  required_version = ">= 1.11, < 2.0"
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "= 3.4.0"
    }
  }
}

# Credentials come from the operator's reviewed OpenStack environment/clouds file.
# No credential values, state backend or cloud account are supplied by this repository.
provider "openstack" {
  region = var.region
}
