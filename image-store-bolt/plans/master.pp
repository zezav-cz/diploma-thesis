# Install Puppet agent and upload per-target config files
# @param targets The targets to run the plan on
plan image_store::master(
  TargetSpec $targets,
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

    class { 'seaweedfs::master':
      ensure               => $ensure,
      port                 => 7010,
      metrics_port         => 7011,
      volume_preallocation => false,
      volume_max           => 30000,
      log_level            => 4,
      kwargs               => {
        '-defaultReplication' => '001',
      },
      config_master        => {
        'master.volume_growth' => {
          'copy_other' => '1',
          'copy_0'     => '1',
        },
      },
      require              => Class['seaweedfs::binary'],
    }

    class { 'seaweedfs::admin':
      port      => 7030,
      ensure    => $ensure,
      masters   => ['redacted'],
      log_level => 4,
      require   => [Class['seaweedfs::binary'], Class['seaweedfs::master']],
    }

    class { 'seaweedfs::filer':
      ensure        => $ensure,
      masters       => [''],
      collection    => 'image_store',
      port          => 7020,
      metrics_port  => 7021,
      readonly_port => 7025,
      log_level     => 4,
      kwargs        => {
        '-defaultReplicaPlacement' => '001',
        '-disk'                    => 'nvme',
      },
      config_filer  => {
        'filer.options' => {
          'recursive_delete'     => 'false',
          'max_file_name_length' => '255',
        },
        'leveldb2'      => {
          'enabled' => 'false',
        },
        postgres2       => {
          'enabled'     => 'true',
          'hostname'    => 'redacted',
          'port'        => '5432',
          'username'    => 'seaweedfs',
          'password'    => 'redacted',
          'database'    => 'seaweedfs',
          'sslmode'     => 'require',
          'createTable' => 'CREATE TABLE IF NOT EXISTS "%s" (dirhash BIGINT,name VARCHAR(65535),directory VARCHAR(65535),meta bytea,PRIMARY KEY (dirhash, name));',
        },
      },
      require       => [Class['seaweedfs::binary'], Class['seaweedfs::master']],
    }
  }
}
