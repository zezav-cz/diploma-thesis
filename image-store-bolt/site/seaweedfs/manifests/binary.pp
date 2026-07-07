# @summary Deploys seqweedfs binary
# @example
#   include seaweedfs::binary
# @param ensure Whether to ensure the binary is present or absent
# @param enterprise Whether to deploy the enterprise version
# @param version The version of seaweedfs to deploy
# @param bin_dir The target directory to install seaweedfs binary
# @param tar_dir The target directory to store downloaded tarballs
# @param path_add Whether to add seaweedfs to the system PATH
# @param path_dir The directory to add to the system PATH
class seaweedfs::binary (
  Seaweedfs::Ensure $ensure,
  Boolean           $enterprise = $seaweedfs::enterprise,
  String[1]         $version    = $seaweedfs::version,
  String[1]         $bin_dir    = "${seaweedfs::base_dir}/${version}",
  String[1]         $tar_dir    = "${seaweedfs::base_dir}/archives",
  Boolean           $path_add   = true,
  String[1]         $path_dir   = '/usr/local/bin',
) {
  $_arch = $facts['os']['architecture'] ? {
    'aarch64' => 'arm64',
    'amd64' => 'amd64',
    default   => fail("Unsupported architecture ${facts['os']['architecture']}"),
  }
  $_url = $enterprise ? {
    true    => "https://github.com/seaweedfs/artifactory/releases/download/${version}/weed-enterprise-linux_${_arch}.tar.gz",
    default => fail('Only enterprise version is supported at this time'),
  }
  $_basename = $enterprise ? {
    true    => "weed-enterprise-${version}-linux_${_arch}.tar.gz",
    default => fail('Only enterprise version is supported at this time'),
  }

  if !defined(File[$bin_dir]) {
    file { $bin_dir:
      ensure => seaweedfs::ensure_to_file($ensure, 'directory'),
    }
  }
  if !defined(File[$tar_dir]) {
    file { $tar_dir:
      ensure  => seaweedfs::ensure_to_file($ensure, 'directory'),
      purge   => true,
      recurse => true,
    }
  }

  $_file = "${tar_dir}/${_basename}"
  archive { "seaweedfs - ${_file}":
    ensure       => $ensure,
    path         => $_file,
    source       => $_url,
    extract      => true,
    extract_path => $bin_dir,
    cleanup      => true,
    creates      => "${bin_dir}/weed",
  }

  if $path_add {
    file { "${path_dir}/weed":
      ensure  => seaweedfs::ensure_to_file($ensure, 'link'),
      target  => "${bin_dir}/weed",
      require => Archive["seaweedfs - ${_file}"],
    }
  }
}
