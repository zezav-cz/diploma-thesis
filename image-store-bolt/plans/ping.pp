plan image_store::ping(
  TargetSpec $targets,
) {
  $command_results = run_command('id -u', $targets, _catch_errors => true)

  $results = $command_results.reduce({}) |$memo, $result| {
    $target = $result.target.name

    if $result.ok {
      $is_root = $result['stdout'].strip == '0'
      $info = {
        'status'   => 'connected',
        'has_root' => $is_root,
      }
    } else {
      $info = {
        'status' => 'unreachable',
        'error'  => $result.error.message,
      }
    }

    $memo + { $target => $info }
  }

  return $results
}
