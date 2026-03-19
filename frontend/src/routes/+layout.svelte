<script lang="ts">
  import NavBar from '$lib/components/NavBar.svelte';
  import '../app.css';

  let { children } = $props();
</script>

<NavBar />
<main>
  {@render children()}
</main>

<style>
  main { max-width: 80rem; margin: 0 auto; padding: 1.5rem; }
</style>
