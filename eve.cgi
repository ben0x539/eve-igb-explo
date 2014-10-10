#!/usr/bin/env ruby

require 'cgi'
require 'sqlite3'

class UserError < Exception; end

SIG_ID_PATTERN = /^[A-Z]{3}-\d{3}$/
SIG_NAME_PATTERN = /^[A-Za-z', ]*$/
SIG_TYPES = ["", "Unknown", "Wormhole", "Gas Site", "Relic Site", "Data Site", "Combat Site"]

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

def load_signatures(sql, system)
  query = <<-END
    SELECT "sigid", "type", "name", "time"
      FROM "signature"
      WHERE "system" = ?
            AND julianday("time", 'unixepoch') > julianday('now', 'unixepoch', '-2 days')
  END
  sigs = {}
  sql.execute(query, [system]) do |sigid, type, name, time|
    sigs[sigid] = [time, Signature.new(sigid, type, name)]
  end

  sigs
end

def submit()
  data = parse_query_string(STDIN.read(4096))
  raise UserError, "bad password" unless data["password"] == 'fourtwenty'
  system = data["system"]
  if !system || system.empty?
    trusted = ENV["HTTP_EVE_TRUSTED"]
    raise UserError, "error: must give system name or use EVE ingame browser" \
      unless trusted
    raise UserError, "error: must give system name or trust site" \
      unless trusted == "Yes"
    system = ENV["HTTP_EVE_SOLARSYSTEMNAME"]
    raise UserError, "error: couldn't detect system name" unless system
    raise UserError, "error: invalid system name (???)" unless /^[-\w ]+$/.match(system)
  end
  result = nil
  SQLite3::Database.new("eve-igb-explo-db/db.sqlite") do |sql|
    sql.execute <<-END
      CREATE TABLE IF NOT EXISTS "signature" (
        "sigid"  STRING PRIMARY KEY,
        "type"   STRING,
        "name"   STRING,
        "system" STRING,
        "time"   INTEGER
      );
      CREATE TABLE IF NOT EXISTS "group" (
        "id"   INTEGER PRIMARY KEY,
        "name" STRING
      );
      CREATE TABLE IF NOT EXISTS "type" (
        "id"   INTEGER PRIMARY KEY,
        "name" STRING
      );
    END
    sigs = load_signatures(sql, system)
    new_sigs = parse_signatures(data["input"])
    to_log = []
    old_sigs = sigs.dup
    now_str = Time.now.to_i.to_s
    new_sigs.each do |sig|
      old_time, old_sig = sigs[sig.id]
      if !old_sig ||
         (old_sig.type.empty? && !sig.type.empty?) ||
         (old_sig.name.empty? && !sig.name.empty?)
        sigs[sig.id] = [now_str, sig, true]
        to_log << sig
      else
        sigs[sig.id][2] = true
      end
    end

    to_log.each do |sig|
      sql.execute(<<-END, sig.id, sig.type, sig.name, system)
        INSERT OR REPLACE INTO "signature"
            ("sigid", "type", "name", "system", "time")
          VALUES
            (?, ?, ?, ?, strftime('%s', 'now'))
      END
    end

    json_sigs = sigs.values.sort_by{ |time, sig, updated|
      [updated ? 0 : 1, -time.to_i, sig.id]
    }.map { |time, sig, updated|
      sprintf '{"time":%s,"id":"%s","type":"%s","name":"%s","updated":%s}',
        time, sig.id, sig.type, sig.name, !!updated
    }
    result = "[#{json_sigs.join(",")}]"
  end

  result
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
