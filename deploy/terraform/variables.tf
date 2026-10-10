variable "enable_rehearsal" {
  type        = bool
  default     = false
  description = "Explicit operator opt-in; no resource is created by default"
}

variable "region" {
  type        = string
  description = "Reviewed OVHcloud Public Cloud region"
}

variable "image_id" {
  type        = string
  description = "Operator-selected hardened Linux image; compatibility pending"
}

variable "flavor_id" {
  type        = string
  description = "Measured rehearsal capacity, not a production sizing claim"
}

variable "network_id" {
  type        = string
  description = "Existing operator-controlled OVHcloud network"
}

variable "existing_key_pair" {
  type        = string
  description = "Existing public SSH key-pair name; no private key in Terraform"
}

variable "operator_cidr" {
  type        = string
  description = "Narrow IPv4 operator SSH source; no application ingress"
  validation {
    condition = can(cidrnetmask(var.operator_cidr)) && try(
      tonumber(split("/", var.operator_cidr)[1]) >= 24, false
    )
    error_message = "Use a reviewed IPv4 operator source of /24 or narrower."
  }
}
