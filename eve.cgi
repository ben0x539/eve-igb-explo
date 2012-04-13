#!/usr/bin/env ruby

require 'cgi'

class UserError < Exception; end

def parse_query_string(str)
  return {} if !str
  Hash[str.split(/\&/).map {|s| s.split(/=/).map(&CGI.method(:unescape))}]
end

def iterate_data(search)
  File.open("eve-data") do |f|
    f.flock(File::LOCK_SH)
    f.each_line do |l|
      l.chomp!
      unless m = /^time=(\d+) system=([\w-]+) id=([A-Z]{3}-\d{3}) type=(\w+) name="([^"]*)"$/.match(l)
        raise "Couldn't parse data entry: " + l
      end
      if m[3].index(search)
        yield(*m.captures)
      end
    end
  end
end

def check(rest)
  args = parse_query_string(ENV["QUERY_STRING"])
  search, format = args["sig-id"], args["format"]
  raise UserError, "missing search string" if !search || search.empty?
  search.strip!
  raise UserError, "invalid search string" if search == "-" || !/^(?:[a-zA-Z]{0,3}-?|-?\d{0,3}|[a-zA-Z]{0,3}-\d{0,3})$/.match(search)
  current_system = ENV["HTTP_EVE_SOLARSYSTEMNAME"]
  if format == "json"
    result = []
    iterate_data(search) do |*values|
      values << (current_system == values[1]).to_s
      result << ('{"time":%s,"system":"%s","id":"%s","type":"%s","name":"%s","current":%s}' % values)
    end
    "[#{result.join(",")}]"
  else
    result = ""
    iterate_data(search) do |time, system, id, type, name|
      result << "#{Time.at(time.to_i).strftime("%Y-%m-%d %H:%M")} #{system == current_system ? "#{system}(*)" : system} #{id} #{type}#{ name.empty? ? "" : " #{name}"}\n"
    end
    result
  end
end

def log()
  data = begin
           parse_query_string(STDIN.read(1024))
         rescue
          raise UserError, "cannot parse request data"
         end
  raise UserError, "bad password" unless data['password'] == 'secretpassword'
  trusted = ENV["HTTP_EVE_TRUSTED"]
  raise UserError, "must be used with EVE ingame browser" unless trusted
  raise UserError, "error: site must be trusted to detect system name" unless trusted == "Yes"
  system = ENV["HTTP_EVE_SOLARSYSTEMNAME"]
  raise UserError, "error: couldn't detect system name" unless system
  raise UserError, "error: invalid system name (???)" unless /^[\w-]+$/.match(system)

  id_letters, id_digits, type, name =
    [data["sig-id-letters"].upcase, data["sig-id-digits"], data["sig-type"], data["sig-name"]]
  name ||= ""
  id_full = "#{id_letters}-#{id_digits}"
  raise UserError, "invalid id" unless /^[A-Z]{3}-\d{3}$/.match(id_full)
  raise UserError, "invalid type" unless ["Unknown", "Gravimetric", "Magnetometric", "Radar", "Ladar"].include?(type)
  raise UserError, "invalid name" unless /^[A-Za-z' ]*$/.match(name)

  File.open("eve-data", "a") do |f|
    f.flock(File::LOCK_EX)
    f.printf "time=%s system=%s id=%s type=%s name=\"%s\"\n", Time.now.to_i.to_s, system, id_full, type, name
  end

  'logged ' + id_full + ' in ' + system
end

def go()
  result = begin
    path, rest = *(ENV["PATH_INFO"] or "/")[1..-1].split("/", 2)

    case path
    when "check" then check(rest)
    when "log" then log()
    else raise UserError, "nothing to do"
    end
  rescue UserError => e
    puts "Status: 400 Bad Request\r\nContent-type: text/plain\r\n\r\n"
    puts e.to_s
    return
  rescue => e
    puts "Status: 500 Internal Server Error\r\nContent-type: text/plain\r\n\r\n"
    puts e.to_s
    e.backtrace.map(&method(:puts))
    return
  end

  puts "Status: 200 OK\r\nContent-type: text/plain\r\n\r\n"
  puts result.to_s
end

go()
