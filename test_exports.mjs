import('./tools/bundled_asar/index.mjs')
  .then(m => {
    console.log('Available exports:', Object.keys(m));
  })
  .catch(e => console.log('Error:', e.message));