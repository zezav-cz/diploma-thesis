function seaweedfs::ensure_to_file(Seaweedfs::Ensure $ensure, String $ensure_name) >> String {
  if $ensure == 'present' {
    return $ensure_name
  } else {
    return 'absent'
  }
}
