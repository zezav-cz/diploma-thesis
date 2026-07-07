class seaweedfs::filer (
  Seaweedfs::Ensure          $ensure,
  Array[String[1]]           $masters,
  String[1]                  $collection,
  # service options
  String[1]                  $server_name                = $facts['networking']['fqdn'], # -ip
  Stdlib::IP::Address        $ip_bind                    = '0.0.0.0', # -ip.bind
  Optional[Stdlib::Port]     $metrics_port               = undef, # -metricsPort
  Stdlib::Port               $port                       = 8888, # -port
  Optional[Stdlib::Port]     $grpc_port                  = undef, # -port.grpc
  Optional[Stdlib::Port]     $readonly_port              = undef, # -port.readonly
  Integer[1]                 $concurrent_upload_limit_mb = 128, # -concurrentUploadLimitMB
  Optional[String[1]]        $default_replica_placement  = undef, # -defaultReplicaPlacement
  Integer[1]                 $dir_list_limit             = 100000, # -dirListLimit
  Optional[Integer[1]]       $download_max_mbps          = undef, # -downloadMaxMBps
  Boolean                    $encrypt_volume_data        = false, # -encryptVolumeData
  Boolean                    $expose_directory_data      = true, # -exposeDirectoryData
  Optional[String[1]]        $filer_group                = undef, # -filerGroup
  Integer[1]                 $max_mb                     = 4, # -maxMB
  # general common options
  Integer[0,4]               $log_level                  = 0,
  Stdlib::Unixpath           $base_dir                   = "${seaweedfs::base_dir}/filer", # working directory
  Stdlib::Unixpath           $data_dir                   = "${base_dir}/data",
  Stdlib::Unixpath           $bin_dir                    = $seaweedfs::binary::bin_dir,
  String[1]                  $bin                        = 'weed',
  Array[String[1]]           $args                       = [], # CLI
  Hash[String[1], String[1]] $kwargs                     = {}, # CLI
  Seaweedfs::Toml_hash       $config_security            = {}, # security.toml
  Seaweedfs::Toml_hash       $config_filer               = {}, # filer.toml
  Seaweedfs::Toml_hash       $config_notification        = {}, # notification.toml
) {
  # Assert for not implemented features
  if $filer_group != undef {
    fail('filerGroup parameter is not implemented yet')
  }

  # Folder structure
  file { $base_dir:
    ensure => stdlib::ensure($ensure, 'directory'),
  }

  file { $data_dir:
    ensure  => stdlib::ensure($ensure, 'directory'),
    require => File[$base_dir],
  }

  # Configuration files
  if $config_filer != {} {
    seaweedfs::config_file { 'filer':
      config_file => 'filer',
      base_path   => $base_dir,
      toml        => stdlib::merge({
          'filer.options' => {
            'recursive_delete'     => 'false',
            'max_file_name_length' => '255',
          },
          'leveldb2'      => {
            'enabled' => 'true',
            'dir'     => $data_dir,
          },
      }, $config_filer),
      require     => File[$base_dir],
    }
  } else {
    seaweedfs::config_file { 'filer':
      config_file => 'filer',
      base_path   => $base_dir,
      toml        => {
        'filer.options' => {
          'recursive_delete'     => 'false',
          'max_file_name_length' => '255',
        },
        'leveldb2'      => {
          'enabled' => 'true',
          'dir'     => $data_dir,
        },
      },
      require     => File[$base_dir],
    }
  }

  if $config_notification != {} {
    seaweedfs::config_file { 'notification':
      config_file => 'notification',
      base_path   => $base_dir,
      toml        => $config_notification,
      require     => File[$base_dir],
    }
  }

  if $config_security != {} {
    seaweedfs::config_file { 'security':
      config_file => 'security',
      base_path   => $base_dir,
      toml        => $config_security,
      require     => File[$base_dir],
    }
  }

  # Service
  $_service_name = 'seaweedfs-filer'

  $_base_kwargs = {
    '-collection'                => $collection,
    '-concurrentUploadLimitMB'   => String($concurrent_upload_limit_mb),
    '-dirListLimit'              => String($dir_list_limit),
    '-ip'                        => $server_name,
    '-ip.bind'                   => $ip_bind,
    '-master'                    => $masters.join(','),
    '-maxMB'                     => String($max_mb),
    '-port'                      => String($port),
  }

  $_args = $args + (
    ($encrypt_volume_data ? { true => ['-encryptVolumeData'], false => [] }) +
    ($expose_directory_data ? { false => [], true => ['-exposeDirectoryData'] })
  ).unique()

  $_kwargs = stdlib::merge(
    $kwargs,
    $_base_kwargs,
    ($metrics_port ? { undef => {}, default => { '-metricsPort' => String($metrics_port) }, }),
    ($grpc_port ? { undef => {}, default => { '-port.grpc' => String($grpc_port) }, }),
    ($readonly_port ? { undef => {}, default => { '-port.readonly' => String($readonly_port) }, }),
    ($default_replica_placement ? { undef => {}, default => { '-defaultReplicaPlacement' => $default_replica_placement }, }),
    ($download_max_mbps ? { undef => {}, default => { '-downloadMaxMBps' => String($download_max_mbps) }, })
  )

  systemd::unit_file { "${_service_name}.service":
    ensure  => $ensure,
    content => epp('seaweedfs/seaweedfs.service.epp', {
        description => 'SeaweedFS Filer Service',
        component   => 'filer',
        dir         => $base_dir,
        bindir      => $bin_dir,
        bin         => $bin,
        kwargs      => $_kwargs,
        args        => $_args,
        log_level   => $log_level,
    }),
    require => [File[$base_dir], Seaweedfs::Config_file['filer']],
    notify  => Service[$_service_name],
  }

  service { $_service_name:
    ensure  => stdlib::ensure($ensure, 'service'),
    enable  => true,
    require => Systemd::Unit_file["${_service_name}.service"],
  }
}
