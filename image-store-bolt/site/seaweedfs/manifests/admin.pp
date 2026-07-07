class seaweedfs::admin (
  Seaweedfs::Ensure          $ensure,
  Array[String[1]]           $masters,
  # service options
  String[1]                  $server_name        = $facts['networking']['fqdn'], # -ip
  Stdlib::Port               $port               = 23646, # -port
  Optional[Stdlib::Port]     $grpc_port          = undef, # -port.grpc (default port + 1000)
  # general common options
  Integer[0,4]               $log_level          = 0,
  Stdlib::Unixpath           $base_dir           = "${seaweedfs::base_dir}/admin", # working directory
  Stdlib::Unixpath           $data_dir           = "${base_dir}/data",
  Stdlib::Unixpath           $bin_dir            = $seaweedfs::binary::bin_dir,
  String[1]                  $bin                = 'weed',
  Array[String[1]]           $args               = [], # CLI
  Hash[String[1], String[1]] $kwargs             = {}, # CLI
  Seaweedfs::Toml_hash       $config_credentials = {}, # credentials.toml
) {
  # Folder structure
  file { $base_dir:
    ensure => stdlib::ensure($ensure, 'directory'),
  }

  file { $data_dir:
    ensure  => stdlib::ensure($ensure, 'directory'),
    require => File[$base_dir],
  }

  # Configuration files
  if $config_credentials != {} {
    seaweedfs::config_file { 'credentials':
      config_file => 'credentials',
      base_path   => $base_dir,
      toml        => $config_credentials,
      require     => File[$base_dir],
    }
  }

  # Service
  $_service_name = 'seaweedfs-admin'

  $_base_kwargs = {
    '-dataDir'   => $data_dir,
    '-masters'   => $masters.join(','),
    '-port'      => String($port),
  }

  $_kwargs = stdlib::merge(
    $kwargs,
    $_base_kwargs,
    ($grpc_port ? { undef => {}, default => { '-port.grpc' => String($grpc_port) }, })
  )

  systemd::unit_file { "${_service_name}.service":
    ensure  => $ensure,
    content => epp('seaweedfs/seaweedfs.service.epp', {
        description => 'SeaweedFS Admin Service',
        component   => 'admin',
        dir         => $base_dir,
        bindir      => $bin_dir,
        bin         => $bin,
        kwargs      => $_kwargs,
        args        => $args,
        log_level   => $log_level,
    }),
    require => File[$base_dir],
    notify  => Service[$_service_name],
  }

  service { $_service_name:
    ensure  => stdlib::ensure($ensure, 'service'),
    enable  => true,
    require => Systemd::Unit_file["${_service_name}.service"],
  }
}
