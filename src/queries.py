VALIDATE_CREDENTIALS = """
{ rateLimitData { limitPerHour pointsSpentThisHour } }
"""

GET_CHARACTER = """
query GetCharacter($name: String!, $serverSlug: String!, $serverRegion: String!) {
  characterData {
    character(name: $name, serverSlug: $serverSlug, serverRegion: $serverRegion) {
      id
      name
      classID
    }
  }
}
"""

GET_REPORT_FIGHTS = """
query GetReportFights($code: String!) {
  reportData {
    report(code: $code) {
      startTime
      endTime
      region { compactName }
      fights(killType: Kills) {
        id
        encounterID
        name
        keystoneLevel
        startTime
        endTime
        kill
      }
      masterData(translate: true) {
        actors(type: "Player") {
          id
          name
          subType
        }
        abilities {
          gameID
          name
        }
      }
    }
  }
}
"""

GET_CHARACTER_RANKINGS = """
query GetRankings(
  $encounterID: Int!,
  $className: String!,
  $specName: String!,
  $serverRegion: String!,
  $bracket: Int!,
  $page: Int!
) {
  worldData {
    encounter(id: $encounterID) {
      characterRankings(
        className: $className
        specName: $specName
        serverRegion: $serverRegion
        difficulty: 10
        bracket: $bracket
        page: $page
        metric: dps
        includeCombatantInfo: false
        includeOtherPlayers: false
      )
    }
  }
}
"""

GET_REPORT_MASTER_DATA = """
query GetMasterData($code: String!) {
  reportData {
    report(code: $code) {
      masterData(translate: true) {
        actors(type: "Player") {
          id
          name
          subType
        }
        abilities {
          gameID
          name
        }
      }
    }
  }
}
"""

GET_CAST_EVENTS = """
query GetCastEvents(
  $code: String!,
  $fightIDs: [Int]!,
  $sourceID: Int!,
  $startTime: Float!,
  $endTime: Float!
) {
  reportData {
    report(code: $code) {
      events(
        dataType: Casts
        fightIDs: $fightIDs
        sourceID: $sourceID
        startTime: $startTime
        endTime: $endTime
        limit: 10000
        useAbilityIDs: true
      ) {
        nextPageTimestamp
        data
      }
    }
  }
}
"""

GET_DAMAGE_TABLE = """
query GetDamageTable(
  $code: String!,
  $fightIDs: [Int]!,
  $startTime: Float!,
  $endTime: Float!
) {
  reportData {
    report(code: $code) {
      table(
        dataType: DamageDone
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        translate: true
      )
    }
  }
}
"""
