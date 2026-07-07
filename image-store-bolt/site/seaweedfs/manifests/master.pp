class seaweedfs::master (
  Seaweedfs::Ensure          $ensure,
  # service options
  String[1]                  $server_name          = $facts['networking']['fqdn'], # -ip
  Stdlib::IP::Address        $ip_bind              = '0.0.0.0', # -ip.bind
  Optional[Stdlib::Port]     $metrics_port         = undef, # -metricsPort
  Stdlib::Port               $port                 = 9333, # -port
  Optional[Stdlib::Port]     $grpc_port            = undef, # port.grpc
  Boolean                    $volume_preallocation = false, # volume.preallocation
  Integer[1]                 $volume_max           = 30000, # -volumeSizeLimitMB
  # general common options
  Integer[0,4]               $log_level            = 0,
  Stdlib::Unixpath           $base_dir             = "${seaweedfs::base_dir}/master", # working directory
  String[1]                  $metadata_dir         = "${base_dir}/metadata",# -mdir
  Stdlib::Unixpath           $bin_dir              = $seaweedfs::binary::bin_dir,
  String[1]                  $bin                  = 'weed',
  Array[String[1]]           $args                 = [], # CLI
  Hash[String[1], String[1]] $kwargs               = {}, # CLI
  Seaweedfs::Toml_hash       $config_security      = {}, # security-master.tomlk
  Seaweedfs::Toml_hash       $config_master        = {}, # master.toml
) {
  # Folder structure
  file { $base_dir:
    ensure => stdlib::ensure($ensure, 'directory'),
  }

  file { $metadata_dir:
    ensure  => stdlib::ensure($ensure, 'directory'),
    require => File[$base_dir],
  }

  # Configuration files
  if $config_security != {} {
    seaweedfs::config_file { 'security-master':
      config_file => 'security',
      base_path   => $base_dir,
      toml        => $config_security,
      require     => File[$base_dir],
    }
  }

  if $config_master != {} {
    seaweedfs::config_file { 'master':
      config_file => 'master',
      base_path   => $base_dir,
      toml        => $config_master,
      require     => File[$base_dir],
    }
  }

  # Service
  $_service_name = 'seaweedfs-master'

  $_base_kwargs = {
    '-ip'      => $server_name ,
    '-ip.bind' => $ip_bind,
    '-mdir'    => $metadata_dir,
    '-port'    => String($port),
    '-volumeSizeLimitMB' => String($volume_max),
  }

  $_args = $args + ($volume_preallocation ? { true => ['-volumePreallocate'], default => [] }).unique()
  $_kwargs = stdlib::merge(
    $kwargs,
    $_base_kwargs,
    ($metrics_port ? { undef => {}, default => { '-metricsPort' => String($metrics_port) }, }),
    ($grpc_port ? { undef => {}, default => { '-port.grpc' => String($grpc_port) }, })
  )

  systemd::unit_file { "${_service_name}.service":
    ensure  => $ensure,
    content => epp('seaweedfs/seaweedfs.service.epp', {
        description => 'SeaweedFS Master Service',
        component   => 'master',
        dir         => $base_dir,
        bindir      => $bin_dir,
        bin         => $bin,
        kwargs      => $_kwargs,
        args        => $_args,
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
