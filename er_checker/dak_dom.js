// Read rendered public DOM only; no internal API calls or framework state.
() => {
  const text = el => (el?.innerText || '').trim();
  const identity = [...document.querySelectorAll('h2')].find(el => text(el).startsWith('Eternal Return Profile for '));
  const metrics = {};
  for (const h of document.querySelectorAll('h4')) {
    const value = h.parentElement.querySelector('.value');
    if (value) metrics[text(h)] = text(value);
  }
  const rank = document.querySelector('b.rp');
  const rankSection = rank?.closest('section');
  const rows = [...document.querySelectorAll('tbody tr')].filter(row => row.querySelector('td.character'));
  const characters = rows.slice(0, 5).map(row => ({
    name: text(row.querySelector('.character-name')),
    games: text(row.querySelector('.plays')),
    winRate: text(row.querySelector('.win-rate')),
    kills: text(row.querySelector('.avg-kill')),
    damage: text(row.querySelector('.avg-damage'))
  }));
  const games = [...document.querySelectorAll('.play-stat')].slice(0, 20).map(el => {
    const card = el.closest('.content');
    return {header: text(card?.firstElementChild), character: text(card?.querySelector('.character-name')),
      combat: text(el.querySelector('.stat')), combatLabel: text(el.querySelector('.label')),
      damage: text(card?.querySelector('.damage .value'))};
  });
  const body = document.body.innerText;
  const updated = body.split('\n').find(l => /Last Updated|最近更新|최근 업데이트|最終更新|最近更新於/.test(l)) || '';
  const season = body.match(/(?:Season|賽季|시즌|シーズン)\s*S?\d+/i)?.[0] || '';
  const recentEmpty = /沒有記錄|沒有資料|No (?:records|data|games)|기록이 없습니다/i.test(text(document.querySelector('.right')));
  return {name: identity ? text(identity).replace('Eternal Return Profile for ', '') : '', metrics, characters, games,
    rp: text(rank), tier: text(rankSection?.querySelector('.tier')), rank: text(rankSection?.querySelector('.rank')),
    season, updated, recentEmpty, body: body.slice(0, 22000)};
}
