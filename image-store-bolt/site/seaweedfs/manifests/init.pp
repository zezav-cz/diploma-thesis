# Manages the SeaweedFS installation
# @param ensure Whether to ensure the SeaweedFS installation is present or absent
# @param base_dir The base directory for SeaweedFS installation
# @param enterprise Whether to deploy the enterprise version
# @param version The version of SeaweedFS to deploy
# @param create_base_dir Whether to create the base directory
class seaweedfs (
  Seaweedfs::Ensure $ensure          = 'present',
  Stdlib::Unixpath  $base_dir        = '/opt/seaweedfs',
  Boolean           $enterprise      = true,
  String[1]         $version         = '4.00',
  Boolean           $create_base_dir = true,
) {
  if $create_base_dir {
    file { $base_dir:
      ensure => stdlib::ensure($ensure, 'directory'),
      owner  => 'root',
      group  => 'root',
      mode   => '0755',
    }
  }
}
