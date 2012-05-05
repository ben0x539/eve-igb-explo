#!/usr/bin/env ruby

require 'cgi'

class UserError < Exception; end

SIG_ID_PATTERN = /^[A-Z]{3}-\d{3}$/
SIG_NAME_PATTERN = /^[A-Za-z', ]*$/
SIG_TYPES = ["", "Gravimetric", "Magnetometric", "Radar", "Ladar", "Unknown"]

Signature = Struct.new(:id, :type, :name)

def parse_query_string(str)
  res = Hash.new("")
  return res unless str
  str.split(/\&/).each do |s|
    i = s.index("=")
    if i
      res[CGI.unescape(s[0...i])] = CGI.unescape(s[i+1..-1])
    end
  end

  res
end

def shorten(s)
  s[0..30].gsub(/\s+/, " ")
end

def parse_signatures(str)
  res = []
  return res unless str
  str.each_line do |line|
    id, cosmic_signature, type, name = *line.split(/\t/, 5)
    next unless cosmic_signature == "Cosmic Signature"
    raise UserError, "invalid id: #{shorten(id)}" \
      unless SIG_ID_PATTERN.match(id)
    raise UserError, "invalid name: #{shorten(name)}" \
      unless SIG_NAME_PATTERN.match(name)
    raise UserError, "invalid type: #{shorten(type)}" \
      unless SIG_TYPES.include?(type)
    res << Signature.new(id, type, name)
  end

  res
end

def load_signatures(time, system)
  sigs = {}
  time_seconds = time.to_i
  File.open("eve-data") do |f|
    f.flock(File::LOCK_SH)
    f.each_line do |l|
      l.chomp!
      unless m = /^time=(\d+) system="([^"]*)" id=([A-Z]{3}-\d{3}) type=(\w*) name="([^"]*)"$/.match(l)
        raise "Couldn't parse data entry: " + l
      end
      next unless m[2] == system && time_seconds - m[1].to_i < 60*60*24*3
      sigs[m[3]] = [time, Signature.new(*m.captures[2 .. -1])]
    end
  end

  sigs
end

def submit()
  data = parse_query_string(input = STDIN.read(4096))
  raise UserError, "bad password" unless data["password"] == 'secretpassword'
  trusted = ENV["HTTP_EVE_TRUSTED"]
  raise UserError, "must be used with EVE ingame browser" unless trusted
  raise UserError, "error: site must be trusted to detect system name" unless trusted == "Yes"
  system = ENV["HTTP_EVE_SOLARSYSTEMNAME"]
  raise UserError, "error: couldn't detect system name" unless system
  raise UserError, "error: invalid system name (???)" unless /^[-\w ]+$/.match(system)
  now = Time.now
  sigs = load_signatures(now, system)
  new_sigs = parse_signatures(data["sig-input"])
  to_log = []
  old_sigs = sigs.dup
  new_sigs.each do |sig|
    old_time, old_sig = sigs[sig.id]
    if !old_sig ||
       (old_sig.type.empty? && !sig.type.empty?) ||
       (old_sig.name.empty? && !sig.name.empty?)
      sigs[sig.id] = [now, sig]
      to_log << sig
    end
  end

  now_str = now.to_i.to_s
  File.open("eve-data", "a") do |f|
    f.flock(File::LOCK_EX)
    to_log.each do |sig|
      f.printf "time=%s system=\"%s\" id=%s type=%s name=\"%s\"\n",
        now_str, system, sig.id, sig.type, sig.name
    end
  end

  json_sigs = sigs.values.sort_by{|time, sig| time}.map {|time, sig|
    sprintf '{"time":%s,"id":"%s","type":"%s","name":"%s"}',
      time.to_i.to_s, sig.id, sig.type, sig.name
  }
  "[#{json_sigs.join(",")}]"
end

def go()
  result = begin
    submit()
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
