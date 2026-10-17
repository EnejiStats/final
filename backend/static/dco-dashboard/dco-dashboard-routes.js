(function(){

  var routes = {};

routes.stats = { userInfo: '/api/dco/user-info', metrics: '/api/dco/metrics', assignments: '/api/dco/assignments',
acceptAssignment: '/api/dco/accept-assignment', declineAssignment: '/api/dco/decline-assignment', submissions: '/api/dco/submissions',
widgetSubmit: (id) => `/api/dco/${id}/widget/submit`, widgetDraft: (id) => `/api/dco/${id}/widget/save-draft`,
};

routes.finance = {
 userInfo:'/api/dco/user-info',
 metrics:'/api/dco/metrics',
 tokenInfo:'/api/dco/token-info',
 tokenWallet:(id)=>'/api/dco/'+encodeURIComponent(id)+'/token-wallet',
 tokenTransactions:(id)=>'/api/dco/'+encodeURIComponent(id)+'/token-transactions',
 tokenPackages:'/api/dco/token-packages',
 tokenPurchase:'/api/dco/token-purchase',
 tokenPurchaseIntent:'/api/dco/token-purchase/intent',
 tokenPurchaseDetail:(id)=>'/api/dco/token-purchases/'+encodeURIComponent(id),
 earnings:(id)=>'/api/dco/'+encodeURIComponent(id)+'/earnings',
 earningsSummary:(id)=>'/api/dco/'+encodeURIComponent(id)+'/earnings/summary',
 earningsActivities:(id)=>'/api/dco/'+encodeURIComponent(id)+'/earnings/activities',
 earningsRates:(id)=>'/api/dco/'+encodeURIComponent(id)+'/earnings/rates',
 payouts:(id)=>'/api/dco/'+encodeURIComponent(id)+'/payout-requests',
 payoutDetail:(id,p)=>'/api/dco/'+encodeURIComponent(id)+'/payout-requests/'+encodeURIComponent(p),
 withdrawal:(id)=>'/api/dco/'+encodeURIComponent(id)+'/withdrawal-account',
 submissions:(id)=>'/api/dco/'+encodeURIComponent(id)+'/submissions',
 submissionDetail:(id,s)=>'/api/dco/'+encodeURIComponent(id)+'/submissions/'+encodeURIComponent(s),
 submissionSummary:(id)=>'/api/dco/'+encodeURIComponent(id)+'/submissions/summary'
};

routes.registration = {
  userInfo:           '/api/dco/user-info',
  metrics:            '/api/dco/metrics',
  regStats:           '/api/dco/registration-stats',

  registerPlayer:     '/api/auth/register',
  registerClub:       '/api/auth/register',

  registerVenue:      '/api/dco/register-venue',
  dcoVenues:          '/api/dco/venues',
  updateVenue:        (id) => `/api/dco/venues/${id}`,

  updateBio:          '/api/dco/update-bio',
  updateAvailability: '/api/dco/update-availability',
  searchPlayers:      '/api/dco/search-players',
  updateProfile:      '/api/dco/update-profile',
  uploadPhoto:        '/api/dco/upload-photo',
  tokenInfo:          '/api/dco/token-info',

  checkEmail:         '/api/auth/check-email',

  countries:          '/api/public/countries',
  states:             '/api/public/states',
  lgas:               '/api/public/lgas',
  clubs:              '/api/public/clubs',
  venues:             '/api/public/venues',

  positions:          '/api/config/positions',
  playerLevels:       '/api/config/player-levels',
  clubLevels:         '/api/config/club-levels',

  dcoSubmissions:     (id) => `/api/dco/${id}/submissions`,
  dcoEarnings:        (id) => `/api/dco/${id}/earnings`,
  dcoPayout:          (id) => `/api/dco/${id}/payout-requests`,
  dcoWithdrawal:      (id) => `/api/dco/${id}/withdrawal-account`,
  support:            '/api/support/tickets',
  supportChat:        (tid) => `/api/support/chat/${tid}`,
};

/* ── API HELPERS ────────────────────────────────────────────────────────────── */

routes.portal = {
  registrations:'/api/dco/registration-stats', profile:'/api/dco/update-profile',
  availability:'/api/dco/update-availability', bio:'/api/dco/update-bio',
  tokens:'/api/dco/token-info', purchase:'/api/dco/token-purchase', trackerSubmissions:'/api/dco/submissions',
  support:'/api/support/tickets',
  submissions:function(id){return '/api/dco/'+encodeURIComponent(id)+'/submissions'},
  earnings:function(id){return '/api/dco/'+encodeURIComponent(id)+'/earnings'},
  payouts:function(id){return '/api/dco/'+encodeURIComponent(id)+'/payout-requests'},
  withdrawal:function(id){return '/api/dco/'+encodeURIComponent(id)+'/withdrawal-account'},
  chat:function(id){return '/api/support/chat/'+encodeURIComponent(id)}
};

  routes.portal.metrics = routes.stats.metrics;

  routes.portal.assignments = routes.stats.assignments;

  window.DCO_ROUTES = routes;

})();