define seaweedfs::config_file (
  Stdlib::Unixpath     $base_path,
  Seaweedfs::Conf_file $config_file,
  Seaweedfs::Toml_hash $toml,
  Seaweedfs::Ensure    $ensure = 'present',
) {
  if $toml == {} {
    fail("Config file '${config_file}' requires a non-empty 'toml' parameter.")
  }
  file { "${base_path}/${config_file}.toml":
    ensure  => stdlib::ensure($ensure, 'file'),
    content => stdlib::to_toml($toml),
  }
}
