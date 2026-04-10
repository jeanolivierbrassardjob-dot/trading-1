export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');

  // Calendrier économique statique mis à jour quotidiennement
  // Pour une version dynamique, utiliser l'API Finnhub gratuite
  const now = new Date();
  const today = now.toLocaleDateString('fr-CA', {weekday:'long', year:'numeric', month:'long', day:'numeric'});

  // Événements types selon le jour de la semaine
  const dow = now.getDay();
  let events = [];

  if (dow === 1) { // Lundi
    events = [
      {time:'10h00 EST', name:'ISM Manufacturing PMI', currency:'USD', impact:'high'},
      {time:'10h00 EST', name:'Construction Spending', currency:'USD', impact:'low'},
    ];
  } else if (dow === 2) { // Mardi
    events = [
      {time:'08h30 EST', name:'Trade Balance', currency:'USD', impact:'med'},
      {time:'10h00 EST', name:'JOLTS Job Openings', currency:'USD', impact:'med'},
      {time:'14h00 EST', name:'Consumer Credit', currency:'USD', impact:'low'},
    ];
  } else if (dow === 3) { // Mercredi
    events = [
      {time:'08h15 EST', name:'ADP Employment Change', currency:'USD', impact:'high'},
      {time:'10h00 EST', name:'ISM Services PMI', currency:'USD', impact:'high'},
      {time:'14h30 EST', name:'Inventaires pétrole EIA', currency:'USD', impact:'med'},
      {time:'14h00 EST', name:'FOMC Minutes', currency:'USD', impact:'high'},
    ];
  } else if (dow === 4) { // Jeudi
    events = [
      {time:'08h30 EST', name:'Initial Jobless Claims', currency:'USD', impact:'med'},
      {time:'08h30 EST', name:'GDP Growth Rate', currency:'USD', impact:'high'},
      {time:'12h00 EST', name:'Discours membres Fed', currency:'USD', impact:'med'},
    ];
  } else if (dow === 5) { // Vendredi
    events = [
      {time:'08h30 EST', name:'Non-Farm Payrolls', currency:'USD', impact:'high'},
      {time:'08h30 EST', name:'Unemployment Rate', currency:'USD', impact:'high'},
      {time:'10h00 EST', name:'Michigan Consumer Sentiment', currency:'USD', impact:'med'},
    ];
  } else {
    events = [
      {time:'—', name:'Marché fermé (weekend)', currency:'—', impact:'low'},
    ];
  }

  return res.status(200).json({ date: today, events });
}
