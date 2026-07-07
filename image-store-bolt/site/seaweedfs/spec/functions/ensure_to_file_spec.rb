# frozen_string_literal: true

require 'spec_helper'

describe 'seaweedfs::ensure_to_file' do
  it { is_expected.to run.with_params('present', 'directory').and_return('directory') }
  it { is_expected.to run.with_params('absent', 'directory').and_return('absent') }
  
  it { is_expected.to run.with_params('present', nil).and_raise_error(StandardError) }
  it { is_expected.to run.with_params(nil, 'directory').and_raise_error(StandardError) }
  it { is_expected.to run.with_params(5, 'directory').and_raise_error(StandardError) }
  it { is_expected.to run.with_params('present', 5).and_raise_error(StandardError) }
end
