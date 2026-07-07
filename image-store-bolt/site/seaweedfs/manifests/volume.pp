# @summary
# @
class seaweedfs::volume (
  Seaweedfs::Ensure                                        $ensure,
  String[1]                                                $rack_name,
  String[1]                                                $dc_name,
  Array[String[1]]                                         $masters,
  # service options
  String[1]                                                $server_name                  = $facts['networking']['fqdn'], # -ip
  Stdlib::IP::Address                                      $ip_bind                      = '0.0.0.0', # -ip.bind
  Optional[Stdlib::Port]                                   $metrics_port                 = undef, # -metricsPort
  Stdlib::Port                                             $port                         = 8080, # -port
  Optional[Stdlib::Port]                                   $grpc_port                    = undef, # -port.grpc
  Optional[Stdlib::Port]                                   $public_port                  = undef, # -port.public
  Integer[1]                                               $concurrent_download_limit_mb = 256, # -concurrentDownloadLimitMB
  Integer[1]                                               $concurrent_upload_limit_mb   = 256, # -concurrentUploadLimitMB
  Optional[Variant[Enum['hdd', 'ssd', 'nvme'], String[1]]] $disk                         = undef, # -disk
  Optional[String[1]]                                      $public_url                   = undef, # -publicUrl
  Enum['local', 'proxy', 'redirect']                       $read_mode                    = 'proxy', # -readMode
  # general common options
  Integer[0,4]                                             $log_level                    = 0,
  Stdlib::Unixpath                                         $base_dir                     = "${seaweedfs::base_dir}/volume", # working directory
  Stdlib::Unixpath                                         $data_dir                     = "${base_dir}/data",
  Stdlib::Unixpath                                         $idx_dir                      = "${base_dir}/idx",
  Stdlib::Unixpath                                         $bin_dir                      = $seaweedfs::binary::bin_dir,
  String[1]                                                $bin                          = 'weed',
  Array[String[1]]                                         $args                         = [], # CLI
  Hash[String[1], String[1]]                               $kwargs                       = {}, # CLI
  Seaweedfs::Toml_hash                                     $config_security              = {}, # security.toml
) {
  # Folder structure
  file { $base_dir:
    ensure => stdlib::ensure($ensure, 'directory'),
  }

  file { $data_dir:
    ensure  => stdlib::ensure($ensure, 'directory'),
    require => File[$base_dir],
  }

  file { $idx_dir:
    ensure  => stdlib::ensure($ensure, 'directory'),
    require => File[$base_dir],
  }

  # Configuration files
  if $config_security != {} {
    seaweedfs::config_file { 'security':
      config_file => 'security',
      base_path   => $base_dir,
      toml        => $config_security,
      require     => File[$base_dir],
    }
  }

  # Service
  $_service_name = 'seaweedfs-volume'

  $_base_kwargs = {
    '-concurrentDownloadLimitMB' => String($concurrent_download_limit_mb),
    '-concurrentUploadLimitMB'   => String($concurrent_upload_limit_mb),
    '-dataCenter'                => $dc_name,
    '-dir'                       => $data_dir,
    '-dir.idx'                   => $idx_dir,
    '-ip'                        => $server_name,
    '-ip.bind'                   => $ip_bind,
    '-master'                    => $masters.join(','),
    '-port'                      => String($port),
    '-rack'                      => $rack_name,
    '-readMode'                  => $read_mode,
  }

  $_kwargs = stdlib::merge(
    $kwargs,
    $_base_kwargs,
    ($metrics_port ? { undef => {}, default => { '-metricsPort' => String($metrics_port) }, }),
    ($grpc_port ? { undef => {}, default => { '-port.grpc' => String($grpc_port) }, }),
    ($public_port ? { undef => {}, default => { '-port.public' => String($public_port) }, }),
    ($disk ? { undef => {}, default => { '-disk' => $disk }, }),
    ($public_url ? { undef => {}, default => { '-publicUrl' => $public_url }, })
  )

  systemd::unit_file { "${_service_name}.service":
    ensure  => $ensure,
    content => epp('seaweedfs/seaweedfs.service.epp', {
        description => 'SeaweedFS Volume Service',
        component   => 'volume',
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
