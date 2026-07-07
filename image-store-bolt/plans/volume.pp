# Install Puppet agent and upload per-target config files
# @param targets The targets to run the plan on
plan image_store::volume(
  TargetSpec $targets,
  Array[String[1]] $masters,
  Seaweedfs::Ensure $ensure = 'present',
) {
  $targets.apply_prep
  $resoults = apply($targets) {
    class { 'seaweedfs':
      base_dir => '/srv/seaweedfs',
    }
    class { 'seaweedfs::binary':
      ensure      => $ensure,
    }
    class { 'seaweedfs::volume':
      ensure       => $ensure,
      rack_name    => $facts['rack_name'],
      dc_name      => $facts['dc'],
      masters      => $masters,

      log_level    => 4,
      port         => 7040,
      metrics_port => 7041,
      public_port  => 7045,
      disk         => $facts['disk'],
      public_url   => "${facts['networking']['fqdn']}:7045",
      read_mode    => 'redirect',

      kwargs       => {
        '-max'          => '0',
        '-minFreeSpace' => '50GiB',
      },
      require      => Class['seaweedfs::binary'],
    }
  }
}
